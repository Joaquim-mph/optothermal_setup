import numpy as np

from laser_setup.utils import up_down_ramp, voltage_ds_sweep_ramp, voltage_sweep_ramp


def _assert_no_consecutive_duplicates(values: np.ndarray, tol: float = 1e-12) -> None:
    if values.size <= 1:
        return
    assert np.all(np.abs(np.diff(values)) > tol)


def test_up_down_ramp_invariants():
    ramp = up_down_ramp(-1.0, 1.0, 0.3)
    assert np.isclose(ramp[0], -1.0)
    assert np.isclose(ramp[-1], -1.0)
    assert np.sum(np.isclose(ramp, 1.0)) == 1
    _assert_no_consecutive_duplicates(ramp)

    turning_index = int(np.argmax(ramp))
    assert np.all(np.diff(ramp[: turning_index + 1]) >= -1e-12)
    assert np.all(np.diff(ramp[turning_index:]) <= 1e-12)


def test_voltage_sweep_ramp_invariants():
    ramp = voltage_sweep_ramp(-2.0, 2.0, 0.7)
    assert np.isclose(ramp[0], 0.0)
    assert np.isclose(ramp[-1], 0.0)
    assert np.any(np.isclose(ramp, -2.0))
    assert np.any(np.isclose(ramp, 2.0))
    _assert_no_consecutive_duplicates(ramp)


def test_voltage_sweep_ramp_zero_start():
    ramp = voltage_sweep_ramp(0.0, 1.5, 0.4)
    assert np.isclose(ramp[0], 0.0)
    assert np.isclose(ramp[-1], 0.0)
    assert np.sum(np.isclose(ramp, 1.5)) == 1
    _assert_no_consecutive_duplicates(ramp)


def test_voltage_ds_sweep_ramp_invariants():
    v_start = 0.01
    v_end = -0.01
    v_step = 1e-4
    ramp = voltage_ds_sweep_ramp(v_start, v_end, v_step)
    assert np.isclose(ramp[0], 0.0)
    assert np.isclose(ramp[-1], 0.0)
    assert np.any(np.isclose(ramp, v_start))
    assert np.any(np.isclose(ramp, v_end))
    _assert_no_consecutive_duplicates(ramp)

    zero_window = 5e-4
    large_step = zero_window
    max_step = np.max(np.abs(np.diff(ramp)))
    assert max_step <= large_step + 1e-12

    in_zero = (np.abs(ramp[:-1]) <= zero_window + 1e-12) & (
        np.abs(ramp[1:]) <= zero_window + 1e-12
    )
    if np.any(in_zero):
        assert np.max(np.abs(np.diff(ramp)[in_zero])) <= v_step + 1e-12
