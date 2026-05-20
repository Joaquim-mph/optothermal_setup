import logging
import time

from pymeasure.experiment import FloatParameter

from ..instruments import (TENMA, Clicker, InstrumentManager, Keithley2450,
                           PT100SerialSensor)
from .ChipProcedure import ChipProcedure, LaserMixin, VgMixin
from .utils import Instruments, Parameters

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class It2(VgMixin, LaserMixin, ChipProcedure):
    """Measures time-dependent current across three configurable phases:
    laser off (t1), laser on (t2), and laser off again (t3).
    """
    name = 'I vs t (3-phase)'

    instruments = InstrumentManager()
    meter: Keithley2450 = instruments.queue(**Instruments.Keithley2450)
    tenma_neg: TENMA = instruments.queue(**Instruments.TENMANEG)
    tenma_pos: TENMA = instruments.queue(**Instruments.TENMAPOS)
    tenma_laser: TENMA = instruments.queue(**Instruments.TENMALASER)
    temperature_sensor: PT100SerialSensor = instruments.queue(
        **Instruments.PT100SerialSensor
    )
    clicker: Clicker = instruments.queue(**Instruments.Clicker)

    # Voltage Parameters
    vg_toggle = Parameters.Control.vg_toggle
    vg = Parameters.Control.vg_dynamic
    vds = Parameters.Control.vds

    # Laser Parameters
    laser_toggle = Parameters.Laser.laser_toggle
    laser_wl = Parameters.Laser.laser_wl
    laser_v = Parameters.Laser.laser_v

    # Temperature parameters
    sense_T = Parameters.Instrument.sense_T
    initial_T = Parameters.Control.initial_T
    target_T = Parameters.Control.target_T
    T_start_t = Parameters.Control.T_start_t

    # Timing parameters
    phase1_t = FloatParameter('Phase 1 duration (laser OFF)', units='s', default=30., minimum=0.)
    phase2_t = FloatParameter('Phase 2 duration (laser ON)', units='s', default=60., minimum=0.)
    phase3_t = FloatParameter('Phase 3 duration (laser OFF)', units='s', default=30., minimum=0.)

    # Additional Parameters, preferably don't change
    sampling_t = Parameters.Control.sampling_t
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC

    DATA_COLUMNS = ['t (s)', 'I (A)', 'VL (V)'] + PT100SerialSensor.DATA_COLUMNS
    INPUTS = ChipProcedure.INPUTS + [
        'vds', 'Irange', 'vg_toggle', 'vg',
        'laser_toggle', 'laser_wl', 'laser_v',
        'phase1_t', 'phase2_t', 'phase3_t',
        'sampling_t', 'sense_T', 'initial_T', 'target_T', 'T_start_t', 'NPLC'
    ]
    EXCLUDE = ChipProcedure.EXCLUDE + ['vg_toggle', 'laser_toggle', 'sense_T']
    SEQUENCER_INPUTS = ['vds', 'laser_v', 'vg', 'target_T']

    def connect_instruments(self):
        if not self.vg_toggle:
            self.instruments.disable(self, 'tenma_neg')
            self.instruments.disable(self, 'tenma_pos')
        if not self.laser_toggle:
            self.instruments.disable(self, 'tenma_laser')
        if not self.sense_T:
            self.instruments.disable(self, 'temperature_sensor')
            self.instruments.disable(self, 'clicker')
        if self.target_T == 0:
            self.instruments.disable(self, 'clicker')
        super().connect_instruments()

    def startup(self):
        self.connect_instruments()

        # Keithley 2450 meter
        self.meter.reset()
        self.meter.make_buffer()
        self.meter.apply_voltage(compliance_current=self.Irange * 1.1 or 0.1)
        self.meter.measure_current(
            current=self.Irange, nplc=self.NPLC, auto_range=not bool(self.Irange)
        )

        # TENMA sources
        self.tenma_neg.apply_voltage(0.)
        self.tenma_pos.apply_voltage(0.)
        self.tenma_laser.apply_voltage(0.)

        # Turn on the outputs
        self.meter.enable_source()
        time.sleep(0.5)
        self.tenma_neg.output = True
        self.tenma_pos.output = True
        self.tenma_laser.output = True
        time.sleep(1.)

    def execute(self):
        log.info(
            "Starting the 3-phase measurement "
            f"(t1={self.phase1_t}s, t2={self.phase2_t}s, t3={self.phase3_t}s)"
        )
        total_time = self.phase1_t + self.phase2_t + self.phase3_t
        if total_time <= 0:
            log.error("Total duration must be positive.")
            return

        self.meter.clear_buffer()
        self.meter.source_voltage = self.vds

        if bool(self.initial_T):
            self.clicker.CT = self.initial_T
        self.clicker.set_target_temperature(self.target_T)

        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
            self.tenma_neg.ramp_to_voltage(0)
        else:
            self.tenma_pos.ramp_to_voltage(0)
            self.tenma_neg.ramp_to_voltage(-self.vg)

        phase1_end = self.phase1_t
        phase2_end = phase1_end + self.phase2_t
        phase3_end = total_time

        def measuring_loop(t_end: float, laser_v: float):
            keithley_time = 0.
            while keithley_time < t_end:
                if self.should_stop():
                    if not getattr(self, 'abort_warned', False):
                        log.warning('Measurement aborted')
                        self.abort_warned = True
                    break

                self.emit('progress', 100 * keithley_time / total_time)

                keithley_time, current = self.meter.get_data()

                temperature_data = self.temperature_sensor.data
                if keithley_time > self.T_start_t:
                    self.clicker.go()

                self.emit('results', dict(zip(
                    self.DATA_COLUMNS, [keithley_time, current, laser_v, *temperature_data]
                )))
                time.sleep(self.sampling_t)

        # Phase 1: laser off
        self.tenma_laser.voltage = 0.
        measuring_loop(phase1_end, 0.)
        if self.should_stop():
            return

        # Phase 2: laser on
        self.tenma_laser.voltage = self.laser_v
        measuring_loop(phase2_end, self.laser_v)
        if self.should_stop():
            return

        # Phase 3: laser off again
        self.tenma_laser.voltage = 0.
        measuring_loop(phase3_end, 0.)
