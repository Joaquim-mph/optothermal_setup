from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Dict, Generator, List, Tuple

import numpy as np
try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None
import requests

from .config import CONFIG

log = logging.getLogger(__name__)

_STEP_SNAP_TOL = 1e-12


def _dedup_consecutive(values: np.ndarray, *, tol: float = _STEP_SNAP_TOL) -> np.ndarray:
    """Remove consecutive duplicates within tolerance."""
    if values.size == 0:
        return values
    keep = np.ones(values.size, dtype=bool)
    keep[1:] = np.abs(np.diff(values)) > tol
    return values[keep]


def _step_ramp(a: float, b: float, step: float, *, include_end: bool) -> np.ndarray:
    """Deterministic float ramp with optional endpoint inclusion."""
    if step <= 0:
        raise ValueError("step must be > 0")
    if np.isclose(a, b, atol=_STEP_SNAP_TOL):
        return np.array([float(b)], dtype=float)

    direction = 1.0 if b > a else -1.0
    span = abs(b - a)
    n = int(np.floor((span / step) + _STEP_SNAP_TOL))
    values = a + np.arange(n + 1, dtype=float) * (direction * step)

    if include_end:
        if abs(values[-1] - b) > _STEP_SNAP_TOL:
            values = np.append(values, b)
        else:
            values[-1] = b
    else:
        if abs(values[-1] - b) <= _STEP_SNAP_TOL:
            values = values[:-1]

    return values


def _zero_window_ramp(
    a: float,
    b: float,
    small_step: float,
    large_step: float,
    zero_window: float,
) -> np.ndarray:
    """Ramp from a to b using small steps within +/- zero_window."""
    if small_step <= 0 or large_step <= 0:
        raise ValueError("step must be > 0")
    if zero_window < 0:
        raise ValueError("zero_window must be >= 0")
    if np.isclose(a, b, atol=_STEP_SNAP_TOL):
        return np.array([float(b)], dtype=float)

    direction = 1.0 if b > a else -1.0
    boundaries = []
    if zero_window > 0:
        for boundary in (-zero_window, zero_window):
            if direction > 0 and a < boundary < b:
                boundaries.append(boundary)
            elif direction < 0 and a > boundary > b:
                boundaries.append(boundary)

    boundaries = sorted(boundaries, reverse=direction < 0)
    points = [a] + boundaries + [b]
    segments = []
    for start, end in zip(points[:-1], points[1:]):
        step = (
            small_step
            if max(abs(start), abs(end)) <= zero_window + _STEP_SNAP_TOL
            else large_step
        )
        segment = _step_ramp(start, end, step, include_end=True)
        if segments:
            segment = segment[1:]
        segments.append(segment)

    values = np.concatenate(segments) if segments else np.array([float(a)], dtype=float)
    return _dedup_consecutive(values)


def up_down_ramp(v_start: float, v_end: float, v_step: float) -> np.ndarray:
    """This function returns a ramp array with the voltages to be applied
    for a voltage sweep. It goes from v_start to v_end, then to v_start.
    Includes v_start at both ends and includes v_end once.

    :param v_start: The starting voltage of the sweep
    :param v_end: The ending voltage of the sweep
    :param v_step: The step size of the sweep
    :return: An array with the voltages to be applied
    """
    step = abs(v_step)
    V_up = _step_ramp(v_start, v_end, step, include_end=True)
    V_down = _step_ramp(v_end, v_start, step, include_end=True)[1:]
    V = np.concatenate((V_up, V_down))
    return _dedup_consecutive(V)


def voltage_sweep_ramp(v_start: float, v_end: float, v_step: float) -> np.ndarray:
    """This function returns an array with the voltages to be applied
    for a voltage sweep. It goes from 0 to v_start, then to v_end, then to
    v_start, and finally back to 0. Includes 0 at both ends.

    :param v_start: The starting voltage of the sweep
    :param v_end: The ending voltage of the sweep
    :param v_step: The step size of the sweep
    :return: An array with the voltages to be applied
    """
    step = abs(v_step)
    if np.isclose(v_start, 0.0, atol=_STEP_SNAP_TOL):
        return up_down_ramp(0.0, v_end, step)

    v_i = _step_ramp(0.0, v_start, step, include_end=True)
    v_m1 = _step_ramp(v_start, v_end, step, include_end=True)[1:]
    v_m2 = _step_ramp(v_end, v_start, step, include_end=True)[1:]
    v_f = _step_ramp(v_start, 0.0, step, include_end=True)[1:]
    V = np.concatenate((v_i, v_m1, v_m2, v_f))
    return _dedup_consecutive(V)


def voltage_ds_sweep_ramp(v_start: float, v_end: float, v_step: float) -> np.ndarray:
    """This function returns an array with the voltages to be applied
    for a voltage sweep. It goes from 0 to v_start, then to v_end and finally back to 0.
    If the step size is between 1e-6 and 5e-4, it will only be applied in the
    range -0.5mV to 0.5mV. Otherwise, a step size of 0.5mV will be used.

    :param v_start: The starting voltage of the sweep
    :param v_end: The ending voltage of the sweep
    :param v_step: The step size of the sweep
    :return: An array with the voltages to be applied
    """
    zero_window = 5e-4
    small_step = abs(v_step)
    if 1e-6 <= small_step <= zero_window:
        large_step = zero_window
    else:
        large_step = small_step

    v_i = _zero_window_ramp(0.0, v_start, small_step, large_step, zero_window)
    v_m = _zero_window_ramp(v_start, v_end, small_step, large_step, zero_window)[1:]
    v_f = _zero_window_ramp(v_end, 0.0, small_step, large_step, zero_window)[1:]
    V = np.concatenate((v_i, v_m, v_f))
    return _dedup_consecutive(V)


def get_data_files(pattern: str = '*.csv') -> List[Path]:
    data_path = Path(CONFIG.Dir.data_dir)
    return list(data_path.rglob(pattern))


def iter_file_lines(
    file: str | Path,
    **kwargs
) -> Generator[str, None, None] | None:
    """Reads a file line by line and yields each line.
    Useful for checks on files with large data.

    :param file: The file to read
    :param kwargs: Additional arguments for the open function
    :return: A generator with the lines of the file
    """
    file_path = Path(file)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file}")

    with file_path.open(mode='r', **kwargs) as f:
        for line in f:
            yield line


def remove_empty_data(days: int = 2):
    """This function removes all the empty files in the data folder,
    up to a certain number of days back. Empty files are considered files with
    only the header and no data.
    """
    data = get_data_files()
    data = [file for file in data if (
        datetime.datetime.now() - extract_date_and_number(file)[0]
        ).days <= days]

    at_least_one = False
    for file in data:
        nonheader_count = 0
        for line in iter_file_lines(file):
            if not line.startswith('#'):
                nonheader_count += 1

            if nonheader_count > 1:
                break

        if nonheader_count <= 1:
            at_least_one = True
            file.unlink()
            log.debug(f"Removed empty file: {file}")

    for directory in Path(CONFIG.Dir.data_dir).rglob('*'):
        if directory.is_dir() and not list(directory.iterdir()):
            directory.rmdir()
            log.debug(f"Removed empty directory: {directory}")

    if at_least_one:
        log.info('Empty files removed')


def send_telegram_alert(message: str):
    """Sends a message to all valid Telegram chats on config.Telegram.
    """
    if not (TOKEN := CONFIG.Telegram.get('token', None)):
        log.debug("Telegram token not specified in config.")
        return

    if len(CONFIG.Telegram.chat_ids) == 0:
        log.debug("No chats specified in config.")
        return

    try:
        requests.get("http://www.example.com/", timeout=0.5)
    except requests.RequestException:
        log.error("No internet response. Cannot send Telegram message.")
        return

    message = ''.join(['\\' + c if c in "_*[]()~`>#+-=|{}.!" else c for c in message])
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    for chat_id in CONFIG.Telegram.chat_ids:
        params = {'chat_id': chat_id, 'text': message, 'parse_mode': 'MarkdownV2'}

        requests.post(url, params=params)

    log.debug(f"Sent '{message}' to {CONFIG.Telegram.chat_ids}.")


def get_status_message(timeout: float = .5) -> str:
    """Gets a status message."""
    return 'Ready'


def read_file_parameters(file_path: str | Path) -> Dict[str, str]:
    """Reads the parameters from a PyMeasure data file."""
    parameters = {}
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    for line in iter_file_lines(file_path):
        line = line.strip()
        if not line or line.startswith('#Data:'):
            break           # Stop reading after the data starts

        if ':' in line:
            if line.startswith(('#Parameters:', '#Metadata:')):
                continue    # Skip these lines

            key, value = map(str.strip, line.split(':', 1))
            key = key.lstrip('#\t')
            parameters[key] = value
    return parameters


def read_pymeasure(file_path: str, comment="#") -> Tuple[Dict, "pd.DataFrame"]:
    """Reads the parameters and data from a PyMeasure data file."""
    if pd is None:
        raise ModuleNotFoundError("pandas is required to read PyMeasure results")
    parameters = read_file_parameters(file_path)
    data = pd.read_csv(file_path, comment=comment)
    return parameters, data


def find_dp(df: "pd.DataFrame") -> float:
    """Finds the Dirac Point from an IVg measurement."""
    if pd is None:
        raise ModuleNotFoundError("pandas is required to analyze PyMeasure results")
    from scipy.signal import find_peaks
    R = 1 / df['I (A)']
    peaks, _ = find_peaks(R)
    return df['Vg (V)'][peaks].mean()


def extract_date_and_number(filename: str | Path) -> tuple[datetime.datetime, int]:
    """Extracts the date and number from a file name.

    :param filename: The file name to sort
    :return: A tuple with the date and number of the file
    """
    filename = Path(filename).name
    date_part, number_part = filename.rsplit('_', 1)
    date = datetime.datetime.strptime(date_part[-10:], '%Y-%m-%d')
    number = int(number_part.split('.')[0])
    return date, number


def get_latest_DP(chip_group: str, chip_number: int | str, sample: str, max_files=1) -> float:
    """This function returns the latest Dirac Point found for the specified
    chip group, chip number and sample. This is based on IVg measurements.

    :param chip_group: The chip group name
    :param chip_number: The chip number
    :param sample: The sample name
    :param max_files: The maximum number of files to look for, starting from the
    latest one.
    :return: The latest Dirac Point found
    """
    data_total = get_data_files()
    data_sorted: list[Path] = sorted(data_total, key=extract_date_and_number)
    data_files: list[Path] = [d for d in data_sorted if 'IVg' in str(d.stem)][-1:-max_files-1:-1]
    for file in data_files:
        params, data = read_pymeasure(file)
        if all((
            params['Chip group name'] == chip_group,
            params['Chip number'] == str(chip_number),
            params['Sample'] == sample
        )):
            DP = find_dp(data)
            if not isinstance(DP, float) or np.isnan(DP):
                continue

            log.info(
                f"Dirac Point found for {chip_group} {chip_number} {sample} "
                f"in {file.name}: {DP:.2f} [V]"
            )
            return DP

    log.warning(
        f"Dirac Point not found for {chip_group} {chip_number} {sample}. (Using DP = 0. instead)"
    )
    return 0.


def rename_data_value(original: str, replace: str) -> None:
    """Takes all .csv files in data/**/*.csv, checks for
    headers and replaces all strings matching original with replace

    :param original: The string to replace
    :param replace: The string to replace with
    """
    data_total = get_data_files()
    for file in data_total:
        with file.open('r+') as f:
            lines = f.readlines()

            for i, line in enumerate(lines):
                if line.startswith('#'):
                    lines[i] = line.replace(original, replace)

            f.seek(0)
            f.writelines(lines)
            f.truncate()

    log.info(f"Replaced '{original}' with '{replace}' in all data files.")
