"""
Tektronix AFG31000 Series Arbitrary Function Generator

Supports all AFG31000 models (25 MHz to 250 MHz) via PyVISA.
Connection interfaces: USB, Ethernet/LAN, GPIB
"""

import time
import logging
from typing import Literal, Optional
import numpy as np

from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import strict_discrete_set, strict_range

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class AFG31000(Instrument):
    """
    Tektronix AFG31000 Series Arbitrary Function Generator
    
    Supports standard waveforms (sine, square, pulse, ramp, noise, DC)
    and arbitrary waveform generation with full SCPI command set.
    
    Connection examples:
        USB:      'USB0::0x0699::0x0405::C100101::INSTR'
        Ethernet: 'TCPIP0::192.168.1.100::inst0::INSTR'
        GPIB:     'GPIB0::12::INSTR'
    
    :param adapter: VISA resource string for the instrument
    :param name: Optional name for the instrument
    :param timeout: Communication timeout in milliseconds (default: 10000)
    :param kwargs: Additional arguments passed to Instrument
    """
    
    # Valid waveform shapes
    WAVEFORMS = ['SINusoid', 'SQUare', 'PULSe', 'RAMP', 'PRNoise', 
                 'DC', 'SINC', 'GAUSsian', 'LORentz', 'ERISe', 
                 'EDECay', 'HAVersine']
    
    # Valid impedance settings (numeric values in ohms or INF for high-Z)
    # Note: Device accepts numeric values like 50, 75, 1000, or INF
    IMPEDANCES = [50, 75, 1000, float('inf')]
    
    def __init__(self, adapter, name="Tektronix AFG31000", timeout=10000, **kwargs):
        super().__init__(
            adapter,
            name,
            timeout=timeout,
            includeSCPI=True,
            **kwargs
        )
        
    def check_errors(self):
        """
        Check and retrieve any errors from the instrument error queue.
        Returns list of error tuples (code, message).
        """
        errors = []
        while True:
            error = self.ask("SYSTEM:ERROR?")
            if error.startswith('0') or 'No error' in error:
                break
            errors.append(error)
        return errors
    
    def clear_errors(self):
        """Clear the error queue."""
        self.write("*CLS")
        
    # =========================================================================
    # Channel 1 Properties
    # =========================================================================
    
    ch1_function = Instrument.control(
        "SOURCE1:FUNCTION:SHAPE?", "SOURCE1:FUNCTION:SHAPE %s",
        """Control the waveform shape for channel 1 (str).""",
        validator=strict_discrete_set,
        values=WAVEFORMS
    )
    
    ch1_frequency = Instrument.control(
        "SOURCE1:FREQUENCY?", "SOURCE1:FREQUENCY %g",
        """Control the frequency for channel 1 in Hz (float).""",
        validator=strict_range,
        values=[1e-6, 250e6]
    )
    
    ch1_amplitude = Instrument.control(
        "SOURCE1:VOLTAGE:AMPLITUDE?", "SOURCE1:VOLTAGE:AMPLITUDE %g",
        """Control the amplitude for channel 1 in Vpp (float).""",
        validator=strict_range,
        values=[0.001, 10.0]
    )
    
    ch1_offset = Instrument.control(
        "SOURCE1:VOLTAGE:OFFSET?", "SOURCE1:VOLTAGE:OFFSET %g",
        """Control the DC offset for channel 1 in V (float).""",
        validator=strict_range,
        values=[-5.0, 5.0]
    )
    
    ch1_phase = Instrument.control(
        "SOURCE1:PHASE?", "SOURCE1:PHASE %g",
        """Control the phase for channel 1 in degrees (float).""",
        validator=strict_range,
        values=[-360, 360]
    )
    
    ch1_output = Instrument.control(
        "OUTPUT1:STATE?", "OUTPUT1:STATE %d",
        """Control the output state for channel 1 (bool).""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True
    )
    
    ch1_impedance = Instrument.control(
        "OUTPUT1:IMPEDANCE?", "OUTPUT1:IMPEDANCE %g",
        """Control the output impedance for channel 1 (numeric: 50, 75, 1000, or inf).""",
        validator=strict_discrete_set,
        values=IMPEDANCES
    )
    
    # =========================================================================
    # Channel 2 Properties
    # =========================================================================
    
    ch2_function = Instrument.control(
        "SOURCE2:FUNCTION:SHAPE?", "SOURCE2:FUNCTION:SHAPE %s",
        """Control the waveform shape for channel 2 (str).""",
        validator=strict_discrete_set,
        values=WAVEFORMS
    )
    
    ch2_frequency = Instrument.control(
        "SOURCE2:FREQUENCY?", "SOURCE2:FREQUENCY %g",
        """Control the frequency for channel 2 in Hz (float).""",
        validator=strict_range,
        values=[1e-6, 250e6]
    )
    
    ch2_amplitude = Instrument.control(
        "SOURCE2:VOLTAGE:AMPLITUDE?", "SOURCE2:VOLTAGE:AMPLITUDE %g",
        """Control the amplitude for channel 2 in Vpp (float).""",
        validator=strict_range,
        values=[0.001, 10.0]
    )
    
    ch2_offset = Instrument.control(
        "SOURCE2:VOLTAGE:OFFSET?", "SOURCE2:VOLTAGE:OFFSET %g",
        """Control the DC offset for channel 2 in V (float).""",
        validator=strict_range,
        values=[-5.0, 5.0]
    )
    
    ch2_phase = Instrument.control(
        "SOURCE2:PHASE?", "SOURCE2:PHASE %g",
        """Control the phase for channel 2 in degrees (float).""",
        validator=strict_range,
        values=[-360, 360]
    )
    
    ch2_output = Instrument.control(
        "OUTPUT2:STATE?", "OUTPUT2:STATE %d",
        """Control the output state for channel 2 (bool).""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True
    )
    
    ch2_impedance = Instrument.control(
        "OUTPUT2:IMPEDANCE?", "OUTPUT2:IMPEDANCE %g",
        """Control the output impedance for channel 2 (numeric: 50, 75, 1000, or inf).""",
        validator=strict_discrete_set,
        values=IMPEDANCES
    )
    
    # =========================================================================
    # Convenience Methods
    # =========================================================================
    
    def configure_channel(self, channel: Literal[1, 2],
                         function: str = 'SINusoid',
                         frequency: float = 1000,
                         amplitude: float = 1.0,
                         offset: float = 0.0,
                         phase: float = 0.0,
                         impedance: float = 50):
        """
        Configure a channel with all parameters at once.

        :param channel: Channel number (1 or 2)
        :param function: Waveform shape (default: 'SINusoid')
        :param frequency: Frequency in Hz (default: 1000)
        :param amplitude: Amplitude in Vpp (default: 1.0)
        :param offset: DC offset in V (default: 0.0)
        :param phase: Phase in degrees (default: 0.0)
        :param impedance: Output impedance in ohms: 50, 75, 1000, or inf (default: 50)
        """
        if channel not in [1, 2]:
            raise ValueError("Channel must be 1 or 2")
        
        ch = f"SOURCE{channel}"
        out = f"OUTPUT{channel}"
        
        # Configure in recommended order
        self.write(f"{out}:STATE OFF")  # Turn off output during config
        self.write(f"{ch}:FUNCTION:SHAPE {function}")
        self.write(f"{ch}:FREQUENCY {frequency}")
        self.write(f"{ch}:VOLTAGE:AMPLITUDE {amplitude}")
        self.write(f"{ch}:VOLTAGE:OFFSET {offset}")
        self.write(f"{ch}:PHASE {phase}")
        self.write(f"{out}:IMPEDANCE {impedance}")
        
        # Allow settings to stabilize
        time.sleep(0.1)
        
        # Check for errors
        errors = self.check_errors()
        if errors:
            log.error(f"Configuration errors on channel {channel}: {errors}")
            raise RuntimeError(f"AFG31000 configuration failed: {errors}")
    
    def enable_channel(self, channel: Literal[1, 2]):
        """Enable output on specified channel."""
        if channel == 1:
            self.ch1_output = True
        elif channel == 2:
            self.ch2_output = True
        else:
            raise ValueError("Channel must be 1 or 2")
    
    def disable_channel(self, channel: Literal[1, 2]):
        """Disable output on specified channel."""
        if channel == 1:
            self.ch1_output = False
        elif channel == 2:
            self.ch2_output = False
        else:
            raise ValueError("Channel must be 1 or 2")
    
    def get_channel_config(self, channel: Literal[1, 2]) -> dict:
        """
        Get complete configuration for specified channel.
        
        :param channel: Channel number (1 or 2)
        :return: Dictionary with all channel settings
        """
        if channel == 1:
            return {
                'function': self.ch1_function,
                'frequency': self.ch1_frequency,
                'amplitude': self.ch1_amplitude,
                'offset': self.ch1_offset,
                'phase': self.ch1_phase,
                'output': self.ch1_output,
                'impedance': self.ch1_impedance
            }
        elif channel == 2:
            return {
                'function': self.ch2_function,
                'frequency': self.ch2_frequency,
                'amplitude': self.ch2_amplitude,
                'offset': self.ch2_offset,
                'phase': self.ch2_phase,
                'output': self.ch2_output,
                'impedance': self.ch2_impedance
            }
        else:
            raise ValueError("Channel must be 1 or 2")
    
    # =========================================================================
    # Pulse Configuration (for PULSE waveform)
    # =========================================================================
    
    def configure_pulse(self, channel: Literal[1, 2],
                       frequency: float = 1000,
                       amplitude: float = 1.0,
                       width: Optional[float] = None,
                       duty_cycle: Optional[float] = None,
                       rise_time: float = 8e-9,
                       fall_time: float = 8e-9):
        """
        Configure pulse waveform on specified channel.
        
        :param channel: Channel number (1 or 2)
        :param frequency: Pulse frequency in Hz
        :param amplitude: Pulse amplitude in Vpp
        :param width: Pulse width in seconds (mutually exclusive with duty_cycle)
        :param duty_cycle: Duty cycle in percent (mutually exclusive with width)
        :param rise_time: Rise time in seconds (default: 8ns)
        :param fall_time: Fall time in seconds (default: 8ns)
        """
        if channel not in [1, 2]:
            raise ValueError("Channel must be 1 or 2")
        
        if width is not None and duty_cycle is not None:
            raise ValueError("Specify either width or duty_cycle, not both")
        
        ch = f"SOURCE{channel}"
        
        # Set to pulse function
        self.write(f"{ch}:FUNCTION:SHAPE PULSe")
        self.write(f"{ch}:FREQUENCY {frequency}")
        self.write(f"{ch}:VOLTAGE:AMPLITUDE {amplitude}")
        
        # Set pulse width or duty cycle
        if width is not None:
            self.write(f"{ch}:PULSE:WIDTH {width}")
        elif duty_cycle is not None:
            self.write(f"{ch}:PULSE:DCYCLE {duty_cycle}")
        else:
            # Default to 50% duty cycle
            self.write(f"{ch}:PULSE:DCYCLE 50")
        
        # Set transition times
        self.write(f"{ch}:PULSE:TRANSITION:LEADING {rise_time}")
        self.write(f"{ch}:PULSE:TRANSITION:TRAILING {fall_time}")
        
        time.sleep(0.1)
        
        # Check for errors
        errors = self.check_errors()
        if errors:
            log.error(f"Pulse configuration errors on channel {channel}: {errors}")
            raise RuntimeError(f"Pulse configuration failed: {errors}")
    
    # =========================================================================
    # Arbitrary Waveform Support
    # =========================================================================
    
    def upload_arbitrary_waveform(self, channel: Literal[1, 2], 
                                  waveform: np.ndarray,
                                  name: str = "USER"):
        """
        Upload arbitrary waveform to instrument memory.
        
        :param channel: Channel number (1 or 2)
        :param waveform: NumPy array with normalized values (-1.0 to +1.0)
        :param name: Waveform name (default: "USER")
        
        Note: Waveform is automatically converted to 14-bit integer format.
        """
        if channel not in [1, 2]:
            raise ValueError("Channel must be 1 or 2")
        
        # Normalize waveform to -1.0 to +1.0 range
        waveform = np.clip(waveform, -1.0, 1.0)
        
        # Convert to 14-bit integer format (0 to 16383)
        waveform_int = ((waveform + 1.0) / 2.0 * 16383).astype(np.uint16)
        
        # Format as comma-separated string
        waveform_str = ','.join(map(str, waveform_int))
        
        # Upload waveform
        ch = f"SOURCE{channel}"
        self.write(f"TRACE:DEF {name},{len(waveform)}")
        self.write(f"TRACE:DATA {name},{waveform_str}")
        
        # Select the uploaded waveform
        self.write(f"{ch}:FUNCTION:SHAPE USER")
        self.write(f"{ch}:FUNCTION:USER {name}")
        
        # Verify upload
        errors = self.check_errors()
        if errors:
            log.error(f"Waveform upload errors on channel {channel}: {errors}")
            raise RuntimeError(f"Waveform upload failed: {errors}")
        
        log.info(f"Successfully uploaded waveform '{name}' ({len(waveform)} points) to channel {channel}")
    
    # =========================================================================
    # Trigger Configuration
    # =========================================================================
    
    def configure_trigger(self, source: str = 'IMMediate'):
        """
        Configure trigger source.
        
        :param source: Trigger source ('IMMediate', 'EXTernal', 'TIMer', 'BUS')
        """
        valid_sources = ['IMMediate', 'EXTernal', 'TIMer', 'BUS']
        if source not in valid_sources:
            raise ValueError(f"Source must be one of {valid_sources}")
        
        self.write(f"TRIGGER:SOURCE {source}")
    
    def trigger(self):
        """Send a software trigger."""
        self.write("*TRG")
    
    # =========================================================================
    # Burst Mode
    # =========================================================================
    
    def configure_burst(self, channel: Literal[1, 2],
                       mode: str = 'TRIGgered',
                       ncycles: int = 1):
        """
        Configure burst mode on specified channel.
        
        :param channel: Channel number (1 or 2)
        :param mode: Burst mode ('TRIGgered' or 'GATed')
        :param ncycles: Number of cycles per burst (triggered mode only)
        """
        if channel not in [1, 2]:
            raise ValueError("Channel must be 1 or 2")
        
        ch = f"SOURCE{channel}"
        
        self.write(f"{ch}:BURST:MODE {mode}")
        if mode == 'TRIGgered':
            self.write(f"{ch}:BURST:NCYCLES {ncycles}")
        self.write(f"{ch}:BURST:STATE ON")
    
    def disable_burst(self, channel: Literal[1, 2]):
        """Disable burst mode on specified channel."""
        if channel not in [1, 2]:
            raise ValueError("Channel must be 1 or 2")
        
        self.write(f"SOURCE{channel}:BURST:STATE OFF")
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def reset(self):
        """Reset instrument to default settings."""
        self.write("*RST")
        self.clear_errors()
        time.sleep(1)  # Allow reset to complete
    
    def all_outputs_off(self):
        """Turn off all outputs."""
        self.ch1_output = False
        self.ch2_output = False
    
    def shutdown(self):
        """Safe shutdown - turn off outputs and close connection."""
        try:
            self.all_outputs_off()
        except Exception as e:
            log.warning(f"Error disabling outputs during shutdown: {e}")
        finally:
            super().shutdown()
