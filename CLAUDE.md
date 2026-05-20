# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Laser Setup is an experimental control system for laser characterization, I-V measurements, and transfer curve measurements. Built on PyMeasure, it provides a Qt-based GUI with YAML-driven configuration (OmegaConf/Hydra) for managing instruments and measurement procedures.

## Key Commands

### Installation & Development Workflow
```bash
# Install in editable mode (recommended for development)
pip install -e .

# After making code changes, ALWAYS rebuild
rm -rf build/
pip install -e .

# Alternative: using uv
uv pip install --editable .
```

**CRITICAL**: After ANY code changes to procedures, instruments, or display code, you MUST run `rm -rf build/ && pip install -e .` before testing. The `build/` directory contains cached compiled code that won't update otherwise.

### Running the Application
```bash
laser_setup                    # Launch main GUI
laser_setup <procedure_name>   # Run specific procedure
laser_setup <script_name>      # Run specific script (e.g., init, setup_adapters)
laser_setup -d                 # Debug mode (DebugInstrument fallback for all connections)
python -m laser_setup          # Alternative launch method
```

### Testing & Linting
```bash
pytest tests/test_ramp.py      # Unit tests (hardware-free)
# Other tests/test_*.py are hardware smoke tests requiring physical devices
flake8 laser_setup tests       # Lint both source and test directories
# Optional stricter type checking:
pyright laser_setup
```

## Architecture

### Configuration System (Hydra/OmegaConf)

The codebase uses a multi-layer YAML configuration system managed by `ConfigHandler`:

1. **Default configuration** (`AppConfig` dataclass in `laser_setup/config/defaults.py`)
2. **Global configuration** (path from default config or `CONFIG` env var → `config/config.yaml`)
3. **Local configuration** (path from global config)

Config files are located in `laser_setup/assets/templates/` (bundled defaults) and user-level in `config/` (project root):
- `config.yaml` - Main application settings (window size, paths, GUI, Telegram, Filename)
- `instruments.yaml` - Instrument definitions and adapter strings
- `procedures.yaml` - Procedure-specific parameter overrides
- `sequences.yaml` - Sequence definitions grouping multiple procedures
- `parameters.yaml` - Global parameter configurations (shared defaults)

`laser_setup/config/config.py` registers OmegaConf resolvers (`${class:...}`, `${function:...}`, `${sequence:...}`) and merges all YAML files into a single `CONFIG` object via `load_and_merge()`.

### Procedure Hierarchy

All measurement procedures inherit from `BaseProcedure` (extends PyMeasure's `Procedure`). The typical hierarchy:

```
BaseProcedure (skip_startup/shutdown, info, show_more)
└── ChipProcedure (chip_group, chip_number, sample + Telegram alert on finish)
    ├── LaserMixin  (zeros laser_v when laser_toggle=False)
    ├── VgMixin     (resolves vg from expression, supports "DP" dirac point lookup)
    └── Concrete procedures: IV, IVg, It, ItVg, ItWl, Vt, VVg, Stress, etc.
```

Key aspects of `BaseProcedure`:
- **Parameters**: Use PyMeasure types (`FloatParameter`, `BooleanParameter`, `ListParameter`) with `group_by` for conditional visibility
- **INPUTS**: List of parameter names to display in GUI
- **EXCLUDE**: Parameters to omit from saved CSV
- **DATA_COLUMNS**: Output columns (first two auto-plotted as X vs Y; put time as 3rd+)
- **Lifecycle**: `startup()` → `connect_instruments()` → `execute()` [emit results] → `shutdown()`
- **`patch_parameters()`**: Called before execute begins. Override in mixins/subclasses to compute derived parameter values (e.g. resolving vg expression, zeroing laser voltage). Call `super().patch_parameters()` at the end.

The `@configurable` decorator loads YAML configuration at class definition time via `configure_class()`. It also hooks `__init_subclass__` so each subclass automatically picks up its section from `CONFIG.procedures.<ClassName>`.

**Key Procedures**:
- `IV`: I-V curves with voltage sweep, `n_sweeps` repetitions, saves time column
- `It`: Current vs time with laser ON/OFF cycling, `relax_time` post-cycle measurement
- `IVg`: Transfer curves (I vs gate voltage)
- `LaserCalibration`: Power meter calibration
- `FakeProcedure`: Testing without hardware

### Instrument Management

`InstrumentManager` (`laser_setup/instruments/manager.py`) provides centralized lifecycle management as a **class attribute** on each procedure class (instruments are shared within a procedure class tree, not globally):

```python
class MyProcedure(BaseProcedure):
    instruments = InstrumentManager()
    meter: Keithley2450 = instruments.queue(**Instruments.Keithley2450)
```

Key behaviors:
1. **`instruments.queue(...)`** stores an `InstrumentProxy` (no hardware access)
2. **`connect_all(self)`** in `startup()` replaces proxies with live instrument instances
3. **Serial port detection**: adapter strings starting with `/dev/` or `COM` auto-wrap with `SerialAdapter`
4. **Singleton cache**: instruments keyed by `{ClassName}/{adapter}` — reused across experiments, never shut down between runs (prevents USB "resource busy" errors)
5. **`instruments.disable(self, 'attr_name')`**: replaces an instrument with `DisabledInstrument` (silently ignores all operations, returns `NoOp`) — use in `connect_instruments()` based on parameter values
6. **`DebugInstrument`**: returns random realistic data; used as fallback when `-d` flag is set and a connection fails
7. **`shutdown_all()`**: called on application exit; by default keeps cache (`remove_from_cache=False`)

**Serial Instrument Configuration** (`instruments.yaml`):
```yaml
TENMALASER:
  adapter: /dev/ttyUSB0          # Linux; or COM3 on Windows
  IDN: TENMA 72-2715 V6.6 SN:37793899
  target: ${class:laser_setup.instruments.tenma.TENMA}
  kwargs:
    baudrate: 9600
    timeout: 2
```

### Sequence System

`Sequence` class (`laser_setup/procedures/Sequence.py`) chains multiple procedures:
- Defined in `sequences.yaml` with procedure names or inline configs
- `common_procedure` shares parameters across all procedures in a sequence
- `sequencer` key triggers PyMeasure `SequenceHandler` for parameter sweeps
- Executed via `SequenceWindow`

```yaml
IVSweepVsd:
  name: IV Vsd Sweep (Vg OFF)
  common_procedure: ${class:laser_setup.procedures.ChipProcedure}
  procedures:
  - IV:
      sequencer: |-
        - "vsd_start", "[-1, -2, -3, -4, -5, -6, -7, -8]"
        - "vsd_end", "[1, 2, 3, 4, 5, 6, 7, 8]"
      parameters:
        n_sweeps: {value: 10}
        vg_toggle: {value: false}
```

### GUI Architecture

Three main window types:

1. **MainWindow** (`laser_setup/display/windows/main_window.py`): Entry point with 4 main procedure buttons and a menu bar giving access to all procedures, sequences, and scripts. Splash screen on startup (`laser_setup/assets/img/splash.png`, 300×300px, 1 s minimum). `procedure_types` and `sequence_types` are stored before `create_menu_bar()` pops them from the config dict.

2. **ExperimentWindow**: Runs individual procedures with live plotting and parameter inputs. Generates unique filenames (`data/YYYY-MM-DD/<Procedure>YYYY-MM-DD_<index>.csv`).

3. **SequenceWindow**: Executes procedure sequences with progress tracking.

All windows are managed in `MainWindow.windows` dict to prevent duplicate instances.

### Configuration Registration

The `@configurable` decorator registers classes so they appear in `CONFIG.procedures` or `CONFIG.sequences`. This enables dynamic instantiation via Hydra's `instantiate()` and populates the GUI menus automatically.

### Patches

`laser_setup/patches.py` is imported first in `__init__.py` to monkey-patch PyMeasure classes before they're used (customizes `Results` to respect `EXCLUDE`, backfills missing columns, adds parameter tooltips).

## Important Patterns

1. **Parameter Override Flow**: `procedures.yaml` → `configure_class()` at class definition → `override_parameters()` in `__init__()` → `_apply_parameter_config()`

2. **Skip Flags**: `skip_startup` / `skip_shutdown` wrap the respective methods via `_wrap_skip()`; when `skip_startup=True`, `connect_instruments()` still runs (instruments always connect)

3. **Instrument Proxy Pattern**: Delays hardware initialization until `connect_all()` is called. `InstrumentProxy` uses `Generic[T]` to maintain IDE type hints while deferring instantiation.

4. **Lazy Config Loading**: `Instruments` and `Parameters` in `procedures/utils.py` use module-level lazy singletons (`_get_instruments()`, `_get_parameters()`) to prevent adapter instantiation at import time.

5. **Time Columns**: Place time as the 3rd+ column in `DATA_COLUMNS` so default plots show column 1 vs column 2.

6. **Shutdown Safety**: `BaseProcedure._safe_state_instruments()` runs on every shutdown (normal completion, manual abort, and failure) to ramp TENMA supplies to 0 V (output off) and disable Keithley sources, so the sample is never left biased between runs. On failure (`status == FAILED`), `InstrumentManager.release_all()` also force-closes and evicts cached connections so a wedged USB interface frees without an app restart; manual abort keeps the cache.

## Common Modifications

### Adding a New Procedure

1. Create `laser_setup/procedures/MyProc.py` subclassing `BaseProcedure` or `ChipProcedure`
2. Add parameters, `INPUTS`, `DATA_COLUMNS`, `execute()`
3. Register in `config/procedures.yaml` (or it self-registers via `@configurable`)
4. **REBUILD**: `rm -rf build/ && pip install -e .`

### Adding a New Parameter to a Procedure

1. `my_param = FloatParameter('Description', units='V', default=1.0)`
2. `INPUTS = ParentClass.INPUTS + ['my_param']`
3. **REBUILD**

### Changing Default Parameter Values

Edit `config/procedures.yaml`:
```yaml
ProcedureName:
  parameters:
    parameter_name:
      value: new_value
```

### Connecting Serial Instruments

In `config/instruments.yaml` (or user `config/instruments.yaml`):
- Set `adapter` to `/dev/ttyUSB0` (Linux), `/dev/tty.*` (macOS), or `COMx` (Windows)
- Add `kwargs` with `baudrate` and `timeout`
- Run `laser_setup setup_adapters` to auto-detect VISA instruments

## Testing Without Hardware

```bash
laser_setup -d  # or --debug
```

Failed instrument connections fall back to `DebugInstrument` (returns random realistic data). `DisabledInstrument` (via `instruments.disable()`) silently no-ops all interactions.

## Troubleshooting

1. **"No device found"**: Check adapter address in `config/instruments.yaml` (`ls /dev/tty*` on Linux/macOS)
2. **Program won't start**: Instrument adapter failing at import time. Check recent config changes, ensure lazy loading is intact.
3. **GUI changes not appearing**: Forgot to rebuild — `rm -rf build/ && pip install -e .`
4. **Parameter not in GUI**: Not in `INPUTS` list, or forgot to rebuild.
5. **Config not loading**: Check `CONFIG` env var or that `config/config.yaml` exists; run `laser_setup init` to initialize.
