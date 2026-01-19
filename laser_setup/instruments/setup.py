"""Manages adapter connections to instruments."""
import logging
from pathlib import Path
from typing import Mapping

import pyvisa

from ..config import CONFIG, save_yaml
from ..config.defaults import DefaultPaths, InstrumentConfig

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def get_idn(adapter: str, rm: pyvisa.ResourceManager) -> str | None:
    """Returns the IDN of the device connected to the adapter.
    If no device is connected, returns None.
    """
    try:
        res = rm.open_resource(adapter)
        try:
            return res.query('*IDN?')[:-1]
        except pyvisa.Error as e:
            log.error(f"Error querying *IDN? from {adapter}: {e}")
            return
        finally:
            res.close()
    except pyvisa.VisaIOError as e:
        log.error(f"Visa IO Error: {e}")
        return


def match_idn(
    idn: str, devices: Mapping[str, InstrumentConfig], strict=True
) -> list[str]:
    """Return all matching device keys for a given IDN string.

    If strict is True, checks for exact match. Otherwise, checks for
    substring match.
    """
    def match(idn: str, device_idn: str) -> bool:
        if strict:
            return idn == device_idn
        return idn in device_idn or device_idn in idn

    matches = []
    for key, device in devices.items():
        if match(idn, device.IDN):
            matches.append(key)
    return matches


def select_device_key(
    adapter: str,
    matches: list[str],
    parent=None
) -> str | None:
    """Disambiguate multiple matches by prompting the user.

    If the candidates include TENMA supplies, briefly apply a small voltage
    to the device on the selected adapter so the user can identify it.
    """
    if not matches:
        return None

    tenma_candidates = [key for key in matches if key.upper().startswith('TENMA')]
    use_tenma_probe = len(tenma_candidates) > 1

    if use_tenma_probe:
        log.info(f"Probing TENMA on {adapter} to identify supply role.")
        try:
            from .tenma import TENMA
            tenma = TENMA(adapter)
            tenma.apply_voltage(0.01)
        except Exception as exc:
            log.warning(f"Failed to probe TENMA at {adapter}: {exc}")
        else:
            title = 'TENMA Configuration'
            label = 'Which TENMA shows a voltage?'
            if parent is not None and hasattr(parent, 'select_from_list'):
                choice = parent.select_from_list(title, tenma_candidates, label=label)
            else:
                prompt = f"{label} ({', '.join(tenma_candidates)}): "
                choice = input(prompt)
            try:
                tenma.shutdown()
            except Exception:
                pass
            return choice if choice in tenma_candidates else None

    title = 'Instrument Configuration'
    label = 'Multiple devices match this IDN. Choose one:'
    if parent is not None and hasattr(parent, 'select_from_list'):
        choice = parent.select_from_list(title, matches, label=label)
    else:
        prompt = f"{label} ({', '.join(matches)}): "
        choice = input(prompt)
    return choice if choice in matches else None


def setup(parent=None, visa_library: str = '') -> None:
    save_path = Path(CONFIG.Dir.instruments_file)
    if save_path == DefaultPaths.instruments:
        log.error(
            "Cannot save to default instruments file. "
            "Define a config[Dir][instruments_file] in your config file."
        )

    save_path.parent.mkdir(parents=True, exist_ok=True)

    rm = pyvisa.ResourceManager(visa_library=visa_library)
    resources = rm.list_resources()
    devices = CONFIG.instruments
    missing_ports = []
    missing_devices = [*devices]

    for res in resources:
        if not (idn := get_idn(res, rm)):
            log.warning(f"No device found at {res}.")
            missing_ports.append(res)
            continue

        matches = match_idn(idn, devices, False)
        if not matches:
            log.info(f"Device with IDN '{idn}' exists in port '{res}' but is not in config.")
            missing_ports.append(res)
            continue

        if len(matches) > 1:
            key = select_device_key(res, matches, parent=parent)
            if key is None:
                log.warning(f"Skipping {res}: could not disambiguate {matches}.")
                missing_ports.append(res)
                continue
        else:
            key = matches[0]

        devices[key].adapter = res
        missing_devices.remove(key)
        log.info(f"Device {key} found at {res}.")

    log.info(f"Missing devices: {missing_devices}")
    log.info(f"Missing ports: {missing_ports}")
    log.info(f"Saving instrument configuration to {save_path}.")
    save_yaml(devices, save_path)
