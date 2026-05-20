"""Hardware-free regression tests for abort behaviour of the It / It2
time-vs-current procedures.

Bug: aborting during the first (laser OFF) phase still energised the laser,
because the inner measuring loop only ``break``s out of its own ``while`` loop
without stopping ``execute()``. Execution fell through to the laser-ON phase and
set ``tenma_laser.voltage = laser_v`` before the next loop broke immediately.
"""
from unittest.mock import MagicMock

import pytest

from laser_setup.procedures.It import It
from laser_setup.procedures.It2 import It2
from laser_setup.procedures.Vt import Vt


class RecordingTenma(MagicMock):
    """A MagicMock that records every value assigned to ``voltage``."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        object.__setattr__(self, "voltage_history", [])

    def __setattr__(self, name, value):
        if name == "voltage":
            self.voltage_history.append(value)
        super().__setattr__(name, value)


def _prepare(proc, laser_v=5.0):
    """Wire a procedure instance with mock instruments and aborted state."""
    proc.should_stop = lambda: True  # simulate an abort request from the start

    laser = RecordingTenma()
    proc.tenma_laser = laser
    proc.meter = MagicMock()
    proc.tenma_pos = MagicMock()
    proc.tenma_neg = MagicMock()
    proc.clicker = MagicMock()
    proc.temperature_sensor = MagicMock()

    # Resolve dynamic / typed parameters to plain values (normally done in
    # patch_parameters before execute runs).
    proc.vg = 0.0
    proc.vds = 0.1
    proc.laser_v = laser_v
    proc.sampling_t = 0.01
    proc.T_start_t = 1e9
    proc.initial_T = 0.0
    proc.target_T = 0.0
    return laser


def test_it_does_not_energise_laser_when_aborted():
    proc = It()
    proc.laser_T = 6.0
    laser = _prepare(proc, laser_v=5.0)

    proc.execute()

    assert all(v == 0.0 for v in laser.voltage_history), (
        f"Laser was energised during an abort: {laser.voltage_history}"
    )


def test_it2_does_not_energise_laser_when_aborted():
    proc = It2()
    proc.phase1_t = 2.0
    proc.phase2_t = 2.0
    proc.phase3_t = 2.0
    laser = _prepare(proc, laser_v=5.0)

    proc.execute()

    assert all(v == 0.0 for v in laser.voltage_history), (
        f"Laser was energised during an abort: {laser.voltage_history}"
    )


def test_vt_does_not_energise_laser_when_aborted():
    proc = Vt()
    proc.laser_T = 6.0
    laser = _prepare(proc, laser_v=5.0)

    proc.execute()

    assert all(v == 0.0 for v in laser.voltage_history), (
        f"Laser was energised during an abort: {laser.voltage_history}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
