import logging
import time

from pymeasure.instruments.keithley import Keithley6517B as _Keithley6517B

log = logging.getLogger(__name__)

# Songs for the Keithley to play when it's done with a measurement :)
SONGS: dict[str, list[tuple[float, float]]] = {
    'triad': [(6/4*1000, 0.25), (5/4*1000, 0.25), (1000, 0.25)],
    'A': [(440, 0.2)]
}


class Keithley6517B(_Keithley6517B):
    """Extended Keithley 6517B Electrometer with buffer management and convenience methods.
    
    Key differences from 2450:
    - Always use zero check when changing functions/ranges
    - Perform zero correction for sub-nA measurements
    - No current sourcing (voltage source only)
    - Slower measurement rates but ultra-high sensitivity
    """
    
    buffer_name: str = "defbuffer1"
    
    def __init__(self, adapter: str, name: str = None, **kwargs):
        super().__init__(
            adapter, name or "Keithley 6517B Electrometer", **kwargs
        )
        # Initialize with zero check enabled for safety
        self.enable_zero_check()
    
    def enable_zero_check(self):
        """Enable zero check to protect input and allow safe configuration.
        
        CRITICAL: Always enable zero check before changing measurement functions
        or ranges to protect the sensitive input circuitry.
        """
        self.write(':SYST:ZCH ON')
        log.debug("Zero check enabled")
    
    def disable_zero_check(self):
        """Disable zero check to begin actual measurements.
        
        Call this after configuration is complete and you're ready to measure.
        """
        self.write(':SYST:ZCH OFF')
        log.debug("Zero check disabled - ready to measure")
    
    def perform_zero_correction(self):
        """Acquire and enable zero correction for ultra-low current measurements.
        
        Perform this on the measurement range you'll use, especially for
        currents below 10 nA. Zero check must be enabled first.
        
        Example:
            keithley.enable_zero_check()
            keithley.source_current_range = 2e-12  # 2 pA range
            keithley.perform_zero_correction()
            keithley.disable_zero_check()
            # Now measure...
        """
        # Ensure zero check is on
        zch_status = self.ask(':SYST:ZCH?')
        if '0' in zch_status:
            log.warning("Zero check not enabled. Enabling now...")
            self.enable_zero_check()
            time.sleep(0.5)  # Allow settling
        
        # Acquire zero correction
        self.write(':SYST:ZCOR:ACQ')
        time.sleep(0.5)  # Allow acquisition
        
        # Enable zero correction
        self.write(':SYST:ZCOR ON')
        log.info("Zero correction acquired and enabled")
    
    def configure_buffer(self, size: int = 50000):
        """Configure the reading buffer size.
        
        The 6517B uses a different buffer structure than the 2450.
        Maximum buffer size is typically 50,000 readings.
        
        :param size: Number of readings the buffer can store (max ~50,000)
        """
        if size > 50000:
            log.warning(f"Buffer size {size} exceeds typical maximum. Using 50000.")
            size = 50000
        
        self.write(f':TRAC:POIN {int(size)}')
        self.write(':TRAC:FEED SENS')  # Feed measurements to buffer
        self.write(':TRAC:FEED:CONT NEXT')  # Store next reading
        log.info(f"Buffer configured for {size} readings")
    
    def clear_buffer(self):
        """Clear the reading buffer."""
        self.write(':TRAC:CLE')
        log.debug("Buffer cleared")
    
    def start_buffered_measurement(self, num_readings: int):
        """Start a buffered measurement sequence.
        
        :param num_readings: Number of readings to acquire
        """
        self.write(f':TRIG:COUN {int(num_readings)}')
        self.write(':INIT')
        log.info(f"Started buffered measurement: {num_readings} readings")
    
    def wait_for_buffer(self, timeout: float = 60):
        """Wait for buffered measurement to complete.
        
        :param timeout: Maximum time to wait in seconds
        """
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                log.error("Buffer measurement timeout")
                raise TimeoutError("Buffered measurement did not complete")
            
            # Check if measurement complete
            try:
                self.ask('*OPC?')
                break
            except:
                time.sleep(0.1)
        
        log.debug("Buffer measurement complete")
    
    def get_buffer_data(self) -> list[float]:
        """Retrieve all data from the buffer.
        
        :return: List of measurement readings
        """
        data_str = self.ask(':TRAC:DATA?')
        data_list = data_str.strip().split(',')
        return [float(x) for x in data_list]
    
    def get_buffer_timestamps(self) -> list[float]:
        """Retrieve timestamps from the buffer.
        
        :return: List of relative timestamps in seconds
        """
        time_str = self.ask(':TRAC:DATA:TST:FORM ABS')
        self.write(':TRAC:DATA:TST:FORM REL')  # Use relative timestamps
        
        timestamp_str = self.ask(':TRAC:DATA:TST?')
        timestamps = timestamp_str.strip().split(',')
        return [float(x) for x in timestamps]
    
    def safe_function_change(self, function: str):
        """Safely change measurement function with proper zero check protocol.
        
        :param function: Measurement function ('VOLT', 'CURR', 'RES', 'CHAR')
        
        Example:
            keithley.safe_function_change('CURR')
        """
        valid_functions = ['VOLT', 'CURR', 'RES', 'CHAR']
        if function.upper() not in valid_functions:
            log.error(f"Invalid function: {function}")
            return
        
        # Enable zero check
        self.enable_zero_check()
        time.sleep(0.1)
        
        # Change function
        self.write(f':SENS:FUNC "{function.upper()}"')
        log.info(f"Changed measurement function to {function.upper()}")
        
        # Note: User must disable zero check when ready to measure
    
    def configure_for_femtoamp_measurement(self, current_range: float = 2e-12):
        """Configure for ultra-low current (femtoampere) measurements.
        
        Sets up the instrument with best practices for sub-picoampere work:
        - Enables zero check
        - Sets current range
        - Uses high integration time (5 PLC)
        - Performs zero correction
        - Leaves zero check ON (user must disable when ready)
        
        :param current_range: Current range (e.g., 2e-12 for 2 pA range)
        """
        log.info("Configuring for femtoampere measurements")
        
        # Enable zero check for safe configuration
        self.enable_zero_check()
        time.sleep(0.2)
        
        # Set to current measurement
        self.write(':SENS:FUNC "CURR"')
        
        # Configure range and integration
        self.write(f':SENS:CURR:RANG {current_range}')
        self.write(':SENS:CURR:RANG:AUTO OFF')  # Fixed range for best noise
        self.write(':SENS:CURR:NPLC 5')  # High integration time
        
        # Enable damping for stability
        self.write(':SENS:CURR:DAMP ON')
        
        # Perform zero correction
        self.perform_zero_correction()
        
        log.info(f"Configured for {current_range*1e12:.1f} pA range")
        log.warning("Zero check still enabled - call disable_zero_check() when ready")
    
    def configure_resistance_measurement(
        self, 
        resistance_range: float = 1e6,
        voltage: float = 10,
        vsource_range: int = 10
    ):
        """Configure for resistance measurement with internal voltage source.
        
        :param resistance_range: Expected resistance range (e.g., 1e6 for 1 MΩ)
        :param voltage: Test voltage to apply (max 10V or 1000V depending on range)
        :param vsource_range: Voltage source range (10 or 1000)
        """
        log.info(f"Configuring resistance measurement: {resistance_range:.2e} Ω at {voltage}V")
        
        self.enable_zero_check()
        time.sleep(0.2)
        
        # Set resistance function
        self.write(':SENS:FUNC "RES"')
        self.write(f':SENS:RES:RANG {resistance_range}')
        
        # Configure internal voltage source for resistance
        self.write(f':SENS:RES:VSO:RANG {vsource_range}')
        self.write(f':SENS:RES:VSO:AMPL {voltage}')
        self.write(':SENS:RES:VSO:OPER ON')
        
        log.info("Resistance measurement configured")
        log.warning("Zero check enabled - disable when ready to measure")
    
    def disable_resistance_vsource(self):
        """Disable the internal voltage source used for resistance measurements."""
        self.write(':SENS:RES:VSO:OPER OFF')
        log.info("Resistance V-source disabled")
    
    def beep(self, frequency: float, duration: float):
        """Make the instrument beep.
        
        :param frequency: Frequency in Hz (65 to 2000)
        :param duration: Duration in seconds (0 to 7.9)
        """
        self.write(f':SYST:BEEP {frequency}, {duration}')
    
    def shutdown(self):
        """Safely shutdown the instrument with audible confirmation.
        
        - Disables any voltage source output
        - Enables zero check for protection
        - Plays shutdown song
        """
        log.info("Shutting down Keithley 6517B")
        
        # Safe shutdown sequence
        try:
            self.write(':OUTP OFF')  # Disable voltage source if active
            self.disable_resistance_vsource()  # Disable resistance V-source
        except:
            pass
        
        self.enable_zero_check()  # Protect input
        
        # Play shutdown song
        for freq, t in SONGS['triad']:
            if freq != 0:
                self.beep(freq, t)
            time.sleep(t)
        
        super().shutdown()
        log.info("6517B shutdown complete")


# Example usage specific to electrometer workflow
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize
    keithley = Keithley6517B("GPIB0::27::INSTR")
    
    try:
        # Example 1: Ultra-low current measurement
        keithley.configure_for_femtoamp_measurement(current_range=2e-12)
        time.sleep(1)  # Allow settling
        keithley.disable_zero_check()
        
        # Single reading
        current = keithley.current
        print(f"Current: {current:.3e} A")
        
        # Example 2: Buffered measurement
        keithley.enable_zero_check()
        keithley.configure_buffer(size=100)
        keithley.clear_buffer()
        keithley.disable_zero_check()
        
        keithley.start_buffered_measurement(num_readings=100)
        keithley.wait_for_buffer(timeout=30)
        
        data = keithley.get_buffer_data()
        print(f"Acquired {len(data)} readings")
        
    finally:
        keithley.shutdown()