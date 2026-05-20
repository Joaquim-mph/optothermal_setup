"""Hardware-free tests for safety teardown and USB self-recovery.

Covers:
- TENMA.ramp_to_voltage tolerating a non-numeric voltage read.
- BaseProcedure shutdown wrapper returning outputs to a safe state on every
  outcome, and releasing cached connections only on failure.
- InstrumentManager.release_all force-closing and evicting cached handles.
"""
import os

# Use a headless Qt platform so importing laser_setup never needs a display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock  # noqa: E402

from laser_setup.instruments import TENMA, Keithley2450  # noqa: E402
from laser_setup.instruments.manager import InstrumentManager  # noqa: E402
from laser_setup.procedures.BaseProcedure import BaseProcedure  # noqa: E402


class _FakeTenma:
    """Minimal stand-in exposing a settable ``voltage`` that starts as a str."""
    def __init__(self, initial):
        self._v = initial

    @property
    def voltage(self):
        return self._v

    @voltage.setter
    def voltage(self, value):
        self._v = value


def test_ramp_to_voltage_parseable_string():
    ft = _FakeTenma("0.00")
    # Must not raise even though the getter returns a string.
    TENMA.ramp_to_voltage(ft, 0.0)
    assert ft.voltage == 0.0


def test_ramp_to_voltage_non_numeric_string():
    ft = _FakeTenma("garbage")
    # Non-numeric read falls back to commanding the target directly.
    TENMA.ramp_to_voltage(ft, 1.0)
    assert ft.voltage == 1.0


def _make_proc(status, should_stop):
    proc = BaseProcedure()
    proc.status = status
    proc.should_stop = lambda: should_stop
    proc.tenma = MagicMock(spec=TENMA)
    proc.meter = MagicMock(spec=Keithley2450)
    proc.instruments = MagicMock()
    return proc


def _assert_safe_state(proc):
    proc.tenma.ramp_to_voltage.assert_called_once_with(0.0, vg_step=0.5)
    assert proc.tenma.output is False
    assert proc.meter.source_voltage == 0.0
    proc.meter.disable_source.assert_called_once()


def test_shutdown_normal_completion_safe_state_keeps_cache():
    proc = _make_proc(BaseProcedure.FINISHED, should_stop=False)
    proc.shutdown()
    _assert_safe_state(proc)
    proc.instruments.release_all.assert_not_called()


def test_shutdown_failure_releases_cache():
    proc = _make_proc(BaseProcedure.FAILED, should_stop=False)
    proc.shutdown()
    _assert_safe_state(proc)
    proc.instruments.release_all.assert_called_once()


def test_shutdown_manual_abort_keeps_cache():
    proc = _make_proc(BaseProcedure.ABORTED, should_stop=True)
    proc.shutdown()
    _assert_safe_state(proc)
    proc.instruments.release_all.assert_not_called()


def test_manager_release_all_closes_and_evicts():
    mgr = InstrumentManager()
    # Isolate from the shared class-level cache.
    mgr.instrument_dict = {}
    fake = MagicMock()
    fake.adapter.connection = MagicMock()
    mgr.instrument_dict["Foo/bar"] = fake

    mgr.release_all()

    fake.adapter.connection.close.assert_called_once()
    assert len(mgr.instrument_dict) == 0
