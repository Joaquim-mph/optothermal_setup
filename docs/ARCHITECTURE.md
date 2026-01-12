# Project Architecture

## Overview
`laser_setup` wraps PyMeasure to automate laser, IV, and transfer-curve experiments through a Hydra/OmegaConf configuration layer and a PyQt6 GUI. The architecture centres on configurable PyMeasure `Procedure` subclasses that coordinate instrument drivers, emit measurement data, and hand control back to PyMeasure's experiment runner. The GUI is thin orchestration: it instantiates procedures, queues experiments, and visualises results.

```
CLI / GUI ──► Configuration Loader ──► Procedure Definition ──► PyMeasure Worker Thread
                    │                          │                        │
              YAML templates              InstrumentManager       Results writer
                    │                          │                        │
                Hydra/OmegaConf ───────────────┴─────────────► Data files / plots
```

## Configuration Layer
- Startup (`laser_setup/__main__.py`) calls `config.setup()`, which parses CLI args, initialises logging, and loads a base config (`laser_setup/config/__init__.py`).
- `laser_setup/config/config.py` merges template YAMLs (config, parameters, procedures, sequences, instruments) with user overrides using Hydra resolvers. Lazy loaders in `laser_setup/procedures/utils.py` expose these settings to procedures without instantiating adapters prematurely.
- CLI flags such as `--debug` propagate through `CONFIG._session.args`, enabling simulated hardware via `DebugInstrument`.

## Instrument Abstraction & PyVISA
- Instruments are declared per-procedure as class attributes via `InstrumentManager.queue`, which stores an `InstrumentProxy` containing the target class and adapter metadata (`laser_setup/instruments/manager.py`).
- At runtime, `InstrumentManager.connect_all` replaces proxies with live instrument instances by calling `setup_adapter`. VISA resource strings are handed to the PyMeasure driver, so communication flows through PyVISA adapters internally. Serial ports are auto-wrapped with `SerialAdapter`.
- `laser_setup/instruments/setup.py` is the discovery utility: it opens each VISA resource through `pyvisa.ResourceManager`, sends `*IDN?`, matches the response to configured devices, and writes updated adapter strings back to YAML.
- Device-specific modules such as `laser_setup/instruments/keithley.py`, `tenma.py`, and `serial.py` extend PyMeasure drivers with project-specific behaviour (buffer helpers, safety ramps, threaded readers). A `DebugInstrument` provides synthetic readings when hardware is unavailable.

## Procedure Lifecycle
- All measurements inherit from `BaseProcedure` (`laser_setup/procedures/BaseProcedure.py`), which defines shared parameters (e.g., `skip_startup`), connects instruments in `startup`, and guarantees a `shutdown` sweep via the shared `InstrumentManager`.
- `override_parameters` applies configuration defaults before PyMeasure initialises the procedure. Hooks such as `patch_parameters` (overridden by `ChipProcedure`, `LaserMixin`, `VgMixin`) adjust values just before the experiment runs.
- A concrete example, `IV` (`laser_setup/procedures/IV.py`), queues multiple instruments, resets them in `startup`, and in `execute` orchestrates SCPI commands: ramping TENMA supplies, polling the Keithley, reading PT100 temperatures, and emitting `{'results': …}` dictionaries that match `DATA_COLUMNS`.

## Experiment Orchestration & GUI
- The GUI entry point (`laser_setup/display/app.py`) creates a PyQt application, applies theme settings, and launches either the main menu or an `ExperimentWindow`.
- `ExperimentWindow` (`laser_setup/display/windows/experiment_window.py`) extends PyMeasure’s `ManagedWindowBase`: it instantiates the selected procedure, generates a unique filename (`unique_filename`), wraps it in `Results`, and queues the experiment on PyMeasure’s worker manager. Incoming `results` signals update plots and logs.
- GUI elements (plots, dock widgets, log pane, info pane) make no control decisions—they observe experiment state. A shutdown button calls the shared `InstrumentManager.shutdown_all` so instruments are left safe even if the user aborts.

## Data Handling
- Filenames are configurable (`config.yaml` → `Filename` section) and default to `./data/YYYY-MM-DD/<Procedure>YYYY-MM-DD_<index>.csv`. PyMeasure writes headers (parameters, metadata) and data rows as the procedure emits results.
- Project patches (`laser_setup/patches.py`) customise PyMeasure’s `Results`: parameters listed in `EXCLUDE` stay out of the CSV, missing columns are backfilled with NaNs on reload, and parameter descriptions show up as tooltips in the GUI inputs.
- Post-run maintenance (`laser_setup/utils.py:remove_empty_data`) purges empty files and directories, keeping the data tree lean.

## What’s Core vs. Optional
- **Core runtime**: configuration loader (`laser_setup/config`), instrument definitions and manager (`laser_setup/instruments`), procedure hierarchy (`laser_setup/procedures`), PyMeasure patches (`laser_setup/patches.py`), and the experiment window (`laser_setup/display/windows/experiment_window.py`). These pieces coordinate measurements, speak to hardware, and persist data.
- **Optional / replaceable**: ancillary GUI widgets, the main menu window, documentation and prototype scripts in `docs/`, `log/`, `data/`, and CLI helpers not directly used during measurement sessions. You can strip or replace these without breaking the measurement pipeline.

## Customising Measurements
1. **Adapters**: Update `config/instruments.yaml` (or run the adapter setup script) so each instrument queue entry points to a valid VISA resource or serial port.
2. **Parameters**: Edit `config/parameters.yaml` to set defaults, bounds, and descriptions. These feed into `override_parameters` automatically.
3. **Procedures**: Create a new subclass of `BaseProcedure`, queue instruments, implement `startup` and `execute`, and emit results dicts matching `DATA_COLUMNS`. The rest of the stack—logging, data files, GUI—adapts automatically.
4. **Headless runs**: Because the orchestration relies on PyMeasure, you can bypass the GUI entirely by instantiating procedures and running `Results`/`Manager` directly; the same measurement flow and data persistence apply.
