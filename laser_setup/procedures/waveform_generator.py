"""
Basic Waveform Generator Procedure

Simple procedure to control the AFG31000 function generator
and generate basic waveforms with adjustable parameters.
"""

import time
import logging
from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
    ListParameter,
    BooleanParameter
)

from .BaseProcedure import BaseProcedure
from ..instruments.manager import InstrumentManager
from ..instruments.afg31000 import AFG31000
from .utils import Instruments

log = logging.getLogger(__name__)


class WaveformGenerator(BaseProcedure):
    """
    Basic Waveform Generator

    Control the Tektronix AFG31000 to generate standard waveforms
    with adjustable frequency, amplitude, offset, and phase.

    This procedure configures the function generator and optionally
    monitors the output parameters over time.
    """

    # Queue the AFG31000 instrument
    instruments = InstrumentManager()
    afg: AFG31000 = instruments.queue(**Instruments.AFG31000)

    # === Channel Selection ===
    channel = IntegerParameter(
        'Channel',
        default=1,
        minimum=1,
        maximum=2,
        group_by='channel'
    )

    # === Waveform Configuration ===
    waveform = ListParameter(
        'Waveform Type',
        default='SINusoid',
        choices=['SINusoid', 'SQUare', 'PULSe', 'RAMP', 'PRNoise', 'DC',
                 'SINC', 'GAUSsian', 'LORentz', 'ERISe', 'EDECay', 'HAVersine']
    )

    frequency = FloatParameter(
        'Frequency',
        units='Hz',
        default=1000,
        minimum=1e-6,
        maximum=150e6
    )

    amplitude = FloatParameter(
        'Amplitude',
        units='Vpp',
        default=1.0,
        minimum=0.001,
        maximum=10.0
    )

    offset = FloatParameter(
        'DC Offset',
        units='V',
        default=0.0,
        minimum=-5.0,
        maximum=5.0
    )

    phase = FloatParameter(
        'Phase',
        units='deg',
        default=0.0,
        minimum=-360,
        maximum=360
    )

    impedance = ListParameter(
        'Output Impedance',
        units='Ω',
        default='50',
        choices=['50', '75', '1000', 'High-Z']
    )

    # === Output Control ===
    enable_output = BooleanParameter(
        'Enable Output',
        default=True
    )

    # === Monitoring Options ===
    monitor_time = FloatParameter(
        'Monitor Duration',
        units='s',
        default=10.0,
        minimum=0,
        maximum=3600
    )

    sample_interval = FloatParameter(
        'Sample Interval',
        units='s',
        default=1.0,
        minimum=0.1,
        maximum=60
    )

    # === GUI Configuration ===
    INPUTS = BaseProcedure.INPUTS + [
        'channel',
        'waveform',
        'frequency',
        'amplitude',
        'offset',
        'phase',
        'impedance',
        'enable_output',
        'monitor_time',
        'sample_interval'
    ]

    # Define output data columns
    DATA_COLUMNS = [
        'Time (s)',
        'Frequency (Hz)',
        'Amplitude (V)',
        'Offset (V)',
        'Phase (deg)',
        'Output State'
    ]

    def startup(self):
        """Initialize and configure the function generator."""
        super().startup()  # Connect instruments

        log.info(f"Configuring AFG31000 Channel {self.channel}")
        log.info(f"Waveform: {self.waveform}")
        log.info(f"Frequency: {self.frequency} Hz")
        log.info(f"Amplitude: {self.amplitude} Vpp")
        log.info(f"Offset: {self.offset} V")
        log.info(f"Phase: {self.phase}°")

        # Convert impedance string to numeric
        impedance_map = {
            '50': 50,
            '75': 75,
            '1000': 1000,
            'High-Z': float('inf')
        }
        impedance_value = impedance_map[self.impedance]

        # Make sure output is off during configuration
        self.afg.disable_channel(self.channel)
        time.sleep(0.1)

        # Configure the selected channel
        self.afg.configure_channel(
            channel=self.channel,
            function=self.waveform,
            frequency=self.frequency,
            amplitude=self.amplitude,
            offset=self.offset,
            phase=self.phase,
            impedance=impedance_value
        )

        # Check for errors
        errors = self.afg.check_errors()
        if errors:
            error_msg = f"AFG configuration errors: {errors}"
            log.error(error_msg)
            raise RuntimeError(error_msg)

        log.info("AFG31000 configured successfully")

        # Enable output if requested
        if self.enable_output:
            self.afg.enable_channel(self.channel)
            log.info(f"Channel {self.channel} output ENABLED")
        else:
            log.info(f"Channel {self.channel} output remains DISABLED")

    def execute(self):
        """
        Monitor the function generator settings over time.

        This allows you to verify the output is stable and
        provides a record of the settings used.
        """
        log.info(f"Monitoring output for {self.monitor_time} seconds")
        log.info(f"Sample interval: {self.sample_interval} seconds")

        start_time = time.time()
        sample_count = 0

        # Calculate total samples
        total_samples = int(self.monitor_time / self.sample_interval)
        if total_samples == 0:
            total_samples = 1

        while True:
            # Check if user requested abort
            if self.should_stop():
                log.warning("Monitoring aborted by user")
                break

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # Check if we've reached the monitoring duration
            if elapsed_time >= self.monitor_time:
                break

            # Read current settings from the instrument
            if self.channel == 1:
                current_freq = self.afg.ch1_frequency
                current_amp = self.afg.ch1_amplitude
                current_offset = self.afg.ch1_offset
                current_phase = self.afg.ch1_phase
                output_state = self.afg.ch1_output
            else:
                current_freq = self.afg.ch2_frequency
                current_amp = self.afg.ch2_amplitude
                current_offset = self.afg.ch2_offset
                current_phase = self.afg.ch2_phase
                output_state = self.afg.ch2_output

            # Record data
            data = {
                'Time (s)': elapsed_time,
                'Frequency (Hz)': current_freq,
                'Amplitude (V)': current_amp,
                'Offset (V)': current_offset,
                'Phase (deg)': current_phase,
                'Output State': 1 if output_state else 0
            }

            self.emit('results', data)

            # Update progress
            sample_count += 1
            progress = min(100, (elapsed_time / self.monitor_time) * 100)
            self.emit('progress', progress)

            if sample_count == 1:
                log.info(f"Output configured and stable")
                log.info(f"Measured: {current_freq:.3f} Hz, {current_amp:.3f} Vpp")

            # Wait for next sample
            time.sleep(self.sample_interval)

        log.info(f"Monitoring complete. Collected {sample_count} samples.")

    def shutdown(self):
        """Cleanup: optionally disable output and close connections."""
        log.info("Shutting down function generator")

        # Disable output if it was enabled
        if self.enable_output:
            try:
                self.afg.disable_channel(self.channel)
                log.info(f"Channel {self.channel} output DISABLED")
            except Exception as e:
                log.warning(f"Error disabling output: {e}")

        # Call parent shutdown (closes connections)
        super().shutdown()


class DualChannelWaveforms(BaseProcedure):
    """
    Dual Channel Waveform Generator

    Configure and output waveforms on both channels simultaneously.
    Useful for differential measurements or phase-locked signals.
    """

    instruments = InstrumentManager()
    afg: AFG31000 = instruments.queue(**Instruments.AFG31000)

    # === Channel 1 Configuration ===
    ch1_waveform = ListParameter(
        'Ch1 Waveform',
        default='SINusoid',
        choices=['SINusoid', 'SQUare', 'PULSe', 'RAMP', 'PRNoise', 'DC'],
        group_by='ch1'
    )

    ch1_frequency = FloatParameter(
        'Ch1 Frequency',
        units='Hz',
        default=1000,
        minimum=1e-6,
        maximum=150e6,
        group_by='ch1'
    )

    ch1_amplitude = FloatParameter(
        'Ch1 Amplitude',
        units='Vpp',
        default=1.0,
        minimum=0.001,
        maximum=10.0,
        group_by='ch1'
    )

    ch1_offset = FloatParameter(
        'Ch1 DC Offset',
        units='V',
        default=0.0,
        minimum=-5.0,
        maximum=5.0,
        group_by='ch1'
    )

    ch1_phase = FloatParameter(
        'Ch1 Phase',
        units='deg',
        default=0.0,
        minimum=-360,
        maximum=360,
        group_by='ch1'
    )

    # === Channel 2 Configuration ===
    ch2_waveform = ListParameter(
        'Ch2 Waveform',
        default='SINusoid',
        choices=['SINusoid', 'SQUare', 'PULSe', 'RAMP', 'PRNoise', 'DC'],
        group_by='ch2'
    )

    ch2_frequency = FloatParameter(
        'Ch2 Frequency',
        units='Hz',
        default=1000,
        minimum=1e-6,
        maximum=150e6,
        group_by='ch2'
    )

    ch2_amplitude = FloatParameter(
        'Ch2 Amplitude',
        units='Vpp',
        default=1.0,
        minimum=0.001,
        maximum=10.0,
        group_by='ch2'
    )

    ch2_offset = FloatParameter(
        'Ch2 DC Offset',
        units='V',
        default=0.0,
        minimum=-5.0,
        maximum=5.0,
        group_by='ch2'
    )

    ch2_phase = FloatParameter(
        'Ch2 Phase',
        units='deg',
        default=90.0,  # 90° out of phase by default
        minimum=-360,
        maximum=360,
        group_by='ch2'
    )

    # === Common Settings ===
    enable_ch1 = BooleanParameter(
        'Enable Ch1 Output',
        default=True
    )

    enable_ch2 = BooleanParameter(
        'Enable Ch2 Output',
        default=True
    )

    monitor_time = FloatParameter(
        'Monitor Duration',
        units='s',
        default=10.0,
        minimum=0,
        maximum=3600
    )

    INPUTS = BaseProcedure.INPUTS + [
        'ch1_waveform', 'ch1_frequency', 'ch1_amplitude', 'ch1_offset', 'ch1_phase',
        'ch2_waveform', 'ch2_frequency', 'ch2_amplitude', 'ch2_offset', 'ch2_phase',
        'enable_ch1', 'enable_ch2', 'monitor_time'
    ]

    DATA_COLUMNS = [
        'Time (s)',
        'Ch1 Freq (Hz)', 'Ch1 Amp (V)', 'Ch1 State',
        'Ch2 Freq (Hz)', 'Ch2 Amp (V)', 'Ch2 State'
    ]

    def startup(self):
        """Configure both channels."""
        super().startup()

        log.info("Configuring dual channel output")

        # Disable outputs during configuration
        self.afg.all_outputs_off()
        time.sleep(0.1)

        # Configure Channel 1
        log.info(f"Ch1: {self.ch1_waveform}, {self.ch1_frequency} Hz, {self.ch1_amplitude} Vpp")
        self.afg.configure_channel(
            channel=1,
            function=self.ch1_waveform,
            frequency=self.ch1_frequency,
            amplitude=self.ch1_amplitude,
            offset=self.ch1_offset,
            phase=self.ch1_phase,
            impedance=50
        )

        # Configure Channel 2
        log.info(f"Ch2: {self.ch2_waveform}, {self.ch2_frequency} Hz, {self.ch2_amplitude} Vpp")
        self.afg.configure_channel(
            channel=2,
            function=self.ch2_waveform,
            frequency=self.ch2_frequency,
            amplitude=self.ch2_amplitude,
            offset=self.ch2_offset,
            phase=self.ch2_phase,
            impedance=50
        )

        # Check for errors
        errors = self.afg.check_errors()
        if errors:
            log.error(f"Configuration errors: {errors}")
            raise RuntimeError(f"AFG configuration failed: {errors}")

        # Enable requested channels
        if self.enable_ch1:
            self.afg.enable_channel(1)
            log.info("Channel 1 output ENABLED")

        if self.enable_ch2:
            self.afg.enable_channel(2)
            log.info("Channel 2 output ENABLED")

    def execute(self):
        """Monitor both channels."""
        start_time = time.time()

        while True:
            if self.should_stop():
                break

            elapsed_time = time.time() - start_time
            if elapsed_time >= self.monitor_time:
                break

            # Read both channels
            data = {
                'Time (s)': elapsed_time,
                'Ch1 Freq (Hz)': self.afg.ch1_frequency,
                'Ch1 Amp (V)': self.afg.ch1_amplitude,
                'Ch1 State': 1 if self.afg.ch1_output else 0,
                'Ch2 Freq (Hz)': self.afg.ch2_frequency,
                'Ch2 Amp (V)': self.afg.ch2_amplitude,
                'Ch2 State': 1 if self.afg.ch2_output else 0
            }

            self.emit('results', data)
            self.emit('progress', (elapsed_time / self.monitor_time) * 100)

            time.sleep(1.0)

    def shutdown(self):
        """Disable both outputs."""
        log.info("Disabling outputs")
        try:
            self.afg.all_outputs_off()
        except Exception as e:
            log.warning(f"Error disabling outputs: {e}")

        super().shutdown()
