import logging
import time

from pymeasure.experiment import BooleanParameter, IntegerParameter

from ..instruments import (TENMA, Keithley2450, PT100SerialSensor,
                           InstrumentManager)
from ..utils import sawtooth_ramp
from .ChipProcedure import ChipProcedure, LaserMixin, VgMixin
from .utils import Parameters, Instruments

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class IVsaw(VgMixin, LaserMixin, ChipProcedure):
    """IV measurement with a sawtooth V_ds waveform.

    For each polarity the source-drain voltage starts at 0, ramps linearly
    to the peak (V_end), then ramps steeply back to 0. This cycle is repeated
    n_cycles times. Positive (orange) and negative (blue) polarities are run
    sequentially.
    """
    name = 'I vs V (sawtooth)'

    instruments = InstrumentManager()
    meter: Keithley2450 = instruments.queue(**Instruments.Keithley2450)
    tenma_neg: TENMA = instruments.queue(**Instruments.TENMANEG)
    tenma_pos: TENMA = instruments.queue(**Instruments.TENMAPOS)
    tenma_laser: TENMA = instruments.queue(**Instruments.TENMALASER)
    temperature_sensor: PT100SerialSensor = instruments.queue(
        **Instruments.PT100SerialSensor
    )

    # Voltage parameters
    vg_toggle = Parameters.Control.vg_toggle
    vg = Parameters.Control.vg_dynamic
    vsd_end = Parameters.Control.vsd_end        # Peak positive voltage

    # Sawtooth ramp parameters
    vsd_step = Parameters.Control.vsd_step           # Slow ramp (toward peak)
    vsd_step_fast = Parameters.Control.vsd_step_fast  # Steep ramp (back to 0)
    n_cycles = IntegerParameter('Cycles per polarity', default=2, minimum=1)
    run_positive = BooleanParameter('Run positive sweep', default=True)
    run_negative = BooleanParameter('Run negative sweep', default=True)

    # Laser parameters
    laser_toggle = Parameters.Laser.laser_toggle
    laser_wl = Parameters.Laser.laser_wl
    laser_v = Parameters.Laser.laser_v
    burn_in_t = Parameters.Laser.burn_in_t

    # Instrument parameters
    sense_T = Parameters.Instrument.sense_T
    step_time = Parameters.Control.step_time
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC

    DATA_COLUMNS = (
        ['Vsd (V)', 'I (A)', 't (s)', 'sweep_num', 'polarity']
        + PT100SerialSensor.DATA_COLUMNS
    )
    INPUTS = ChipProcedure.INPUTS + [
        'vg_toggle', 'vg', 'vsd_end', 'vsd_step', 'vsd_step_fast', 'Irange', 'step_time',
        'n_cycles', 'run_positive', 'run_negative',
        'laser_toggle', 'laser_wl', 'laser_v', 'burn_in_t', 'sense_T', 'NPLC',
    ]
    EXCLUDE = ChipProcedure.EXCLUDE + ['vg_toggle', 'laser_toggle', 'sense_T']

    def connect_instruments(self):
        if not self.vg_toggle:
            self.instruments.disable(self, 'tenma_neg')
            self.instruments.disable(self, 'tenma_pos')
        if not self.laser_toggle:
            self.instruments.disable(self, 'tenma_laser')
        if not self.sense_T:
            self.instruments.disable(self, 'temperature_sensor')
        super().connect_instruments()

    def startup(self):
        self.connect_instruments()

        self.meter.reset()
        self.meter.make_buffer()
        self.meter.apply_voltage(compliance_current=self.Irange * 1.1 or 0.1)
        self.meter.measure_current(
            current=self.Irange, nplc=self.NPLC, auto_range=not bool(self.Irange)
        )

        self.tenma_neg.apply_voltage(0.)
        self.tenma_pos.apply_voltage(0.)
        self.tenma_laser.apply_voltage(0.)

        self.meter.enable_source()
        time.sleep(0.5)
        self.tenma_neg.output = True
        self.tenma_pos.output = True
        self.tenma_laser.output = True
        time.sleep(1.)

    def execute(self):
        # Build list of (polarity_label, peak_voltage) to run
        sweeps = []
        if self.run_positive:
            sweeps.append(('positive', abs(self.vsd_end)))
        if self.run_negative:
            sweeps.append(('negative', -abs(self.vsd_end)))

        if not sweeps:
            log.warning('Neither positive nor negative sweep is enabled; nothing to do.')
            return

        # Pre-compute total point count for progress reporting
        total_points = sum(
            len(sawtooth_ramp(v_end, self.vsd_step, self.vsd_step_fast, self.n_cycles))
            for _, v_end in sweeps
        )

        # Apply gate voltage
        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
            self.tenma_neg.ramp_to_voltage(0)
        else:
            self.tenma_pos.ramp_to_voltage(0)
            self.tenma_neg.ramp_to_voltage(-self.vg)

        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(
                f"Laser is ON. Sleeping for {self.burn_in_t} s to let current stabilize."
            )
            time.sleep(self.burn_in_t)

        start_time = time.time()
        points_done = 0

        for sweep_num, (polarity, v_end) in enumerate(sweeps, start=1):
            ramp = sawtooth_ramp(v_end, self.vsd_step, self.vsd_step_fast, self.n_cycles)
            log.info(f"Starting {polarity} sweep ({len(ramp)} points)")

            for vsd in ramp:
                if self.should_stop():
                    log.warning('Measurement aborted')
                    return

                self.emit('progress', 100 * points_done / total_points)
                self.meter.source_voltage = vsd
                time.sleep(self.step_time)

                measurement_time = time.time() - start_time
                current = self.meter.current
                temperature_data = self.temperature_sensor.data

                self.emit('results', dict(zip(
                    self.DATA_COLUMNS,
                    [vsd, current, measurement_time, sweep_num, polarity, *temperature_data]
                )))

                points_done += 1
