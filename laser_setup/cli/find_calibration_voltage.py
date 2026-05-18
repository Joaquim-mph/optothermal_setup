import logging
from pathlib import Path

import numpy as np
import pandas as pd

from laser_setup.display.Qt import QtWidgets
from laser_setup.utils import get_data_files, read_pymeasure

log = logging.getLogger(__name__)


def get_calibration_voltage(calibration_file: pd.DataFrame, power: float) -> float:
    """This function takes a dataframe with a voltage columns and a power column
    (VL (V) and Power (W) respectively). It returns the voltage interpolated at
    the desired power, it does so by using a linear interpolation between the two
    closest points.

    :param calibration_file: Dataframe with a voltage column and a power column
    :param power: Desired power in watts

    :returns: The voltage interpolated at the desired power, -1 if voltage is out of range
    """
    return np.interp(
        power, calibration_file["Power (W)"].values, calibration_file["VL (V)"].values, right=-1
    )


def main(parent=None):
    """Find the corresponding voltages of the given powers from the selected
    calibration curve.
    """
    owns_app = False
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
        owns_app = True

    try:
        initial_path = get_data_files('LaserCalibration*.csv')[-1].parent
    except (IndexError, FileNotFoundError):
        log.error("No calibration files found. Exiting.")
        return

    path_to_files, _ = QtWidgets.QFileDialog.getOpenFileNames(
        parent,
        "Select Calibration to find voltages",
        str(initial_path),
        "CSV files (*.csv);;All files (*.*)",
    )

    if not path_to_files:
        log.warning("No files selected. Exiting.")
        return

    inputs, ok = QtWidgets.QInputDialog.getText(
        parent,
        "Power Input",
        "Enter powers in µW separated by commas:",
    )

    if not ok or not inputs:
        log.warning("No powers entered. Exiting.")
        return

    powers: list[float] = []
    for power in inputs.split(","):
        try:
            powers.append(float(power.strip()))
        except ValueError:
            log.error(f"Invalid input: {power}")

    if not powers:
        log.warning("No valid powers entered. Exiting.")
        return

    lines: list[str] = []
    for path in path_to_files:
        try:
            data = read_pymeasure(path)
            lines.append(f"File: '{Path(path)}'")
            for power in powers:
                voltage = get_calibration_voltage(data[1], power * 1e-6)
                if voltage == -1:
                    lines.append(f"Power: {power:.2f} [µW] \t Voltage: Out of range")
                else:
                    lines.append(f"Power: {power:.2f} [µW] \t Voltage: {voltage:.2f} [V]")
            lines.append("")
        except Exception as e:
            log.error(f"Error processing file {path}: {str(e)}")

    message = "\n".join(lines).rstrip()
    if message:
        log.info("Calibration voltages:\n" + message)
        QtWidgets.QMessageBox.information(parent, "Calibration Voltages", message)

    if owns_app:
        app.quit()


if __name__ == "__main__":
    main()
