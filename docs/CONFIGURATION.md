# Configuration Guide

This project uses OmegaConf + Hydra-style resolvers to build a single runtime
configuration from multiple YAML files. This document describes the config
layer, where each file lives, and how to extend it safely.

## Overview
At startup, the app:
1) Builds a structured default config (dataclasses in `laser_setup/config/defaults.py`).
2) Merges a global config file (if present).
3) Merges a local config file (if present).
4) Loads and merges the auxiliary YAMLs for parameters, procedures, sequences,
   and instruments.

The merge logic is implemented in `laser_setup/config/handler.py` and
`laser_setup/config/config.py`.

## File layout
User-editable runtime files live in the `config/` directory:
- `config/config.yaml` (main application config)
- `config/parameters.yaml` (default parameter definitions)
- `config/procedures.yaml` (procedure-level overrides + class mapping)
- `config/sequences.yaml` (sequence definitions)
- `config/instruments.yaml` (instrument adapters + class mapping)

Templates live under:
- `laser_setup/assets/templates/` (source templates copied by init tools)

## Loading order and overrides
The loader (`ConfigHandler.load_config`) merges in this order:
1) Structured defaults (dataclasses)
2) Global config file, located via:
   - `CONFIG` environment variable, or
   - `Dir.global_config_file` from the defaults
3) Local config file, located via `Dir.local_config_file` in the merged config

If a file does not exist, it is skipped. Later files override earlier ones.

## Hydra-style resolvers in YAML
The config layer registers three resolvers in `laser_setup/config/config.py`:
- `${class:package.module.ClassName}` -> hydra utils class reference
- `${function:package.module.function_name}` -> hydra utils function reference
- `${sequence:SequenceName}` -> dynamic `Sequence` subclass

These appear in the `_types` sections of YAML to map names to import paths.

## Main config (`config/config.yaml`)
This file configures the app and points to the other YAMLs.

Key sections:
- `Dir`: paths for the auxiliary YAMLs, data directory, and database.
- `scripts`: menu entries in the GUI (name + target function).
- `Adapters`: legacy adapter shortcuts used by some procedures.
- `Qt`: GUI style, fonts, main window sizing, and Sequence/Experiment window
  config.
- `Filename`: output filename formatting.
- `Logging`: Python logging configuration.
- `matplotlib_rcParams`: matplotlib defaults (string values only).
- `Telegram`: optional bot integration.

Example:
```yaml
Dir:
  parameters_file: ./config/parameters.yaml
  procedures_file: ./config/procedures.yaml
  sequences_file: ./config/sequences.yaml
  instruments_file: ./config/instruments.yaml
```

## Parameters (`config/parameters.yaml`)
This file defines reusable PyMeasure `Parameter` objects grouped by category.
Each entry includes a `_target_` pointing at a Parameter class and optional
metadata like `default`, `units`, `minimum`, `choices`, and `group_by`.

Structure:
```yaml
_types:
  - &FloatParameter pymeasure.experiment.FloatParameter

Laser:
  laser_v:
    _target_: *FloatParameter
    default: 0.0
    name: Laser voltage
    units: V
```

Notes:
- `group_by` controls UI visibility based on another boolean parameter.
- `Metadata` parameters can use `fget` to read a value from an instrument.

## Procedures (`config/procedures.yaml`)
This file provides per-procedure overrides and the procedure class registry.

Structure:
```yaml
IVg:
  parameters:
    procedure_version:
      value: 2.1.0

_types:
  IVg: ${class:laser_setup.procedures.IVg}
```

Notes:
- The YAML key must match the procedure class name.
- Parameter overrides apply before a procedure instance runs.

## Sequences (`config/sequences.yaml`)
Sequences define ordered steps that run multiple procedures. Each entry can
override parameters or expand a single procedure into multiple steps with a
`sequencer` string.

See `docs/SEQUENCES.md` for full details and an end-to-end example.

## Instruments (`config/instruments.yaml`)
This file maps instrument names to adapters and classes.

Structure:
```yaml
Keithley2450:
  adapter: USB0::0x05E6::0x2450::04448997::0::INSTR
  name: Keithley 2450
  IDN: KEITHLEY
  target: ${class:laser_setup.instruments.keithley.Keithley2450}
  kwargs:
    read_termination: \r\n
```

Notes:
- `adapter` is a VISA resource or serial port.
- `IDN` is used by setup tooling to verify matches.
- `target` uses the `${class:...}` resolver.
- `setup_adapters` can update adapters automatically. If multiple devices share
  the same IDN (e.g., three TENMAs), the tool will prompt you to identify which
  supply lit up after a brief 0.01 V probe so it can assign `TENMANEG`,
  `TENMAPOS`, and `TENMALASER` correctly.

## Template initialization
Use the CLI menu item or script to copy the template config into your local
`config/` directory:
- GUI: `Scripts -> Init Config`
- CLI: `python -m laser_setup` then choose the script, or call
  `laser_setup.cli.init_config.init_config` directly.

## Troubleshooting
- If a procedure or sequence does not appear in the GUI, confirm it is listed
  under `_types` in the corresponding YAML.
- If parameters do not show up, check the `group_by` and `inputs_ignored`
  settings.
- If a config file is not being applied, verify the resolved `Dir.*_file` paths
  and whether a local config overrides the global config.
