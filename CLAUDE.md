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
uv venv
uv pip install .
```

**CRITICAL**: After ANY code changes to procedures, instruments, or display code, you MUST run `rm -rf build/ && pip install -e .` before testing. The `build/` directory contains cached compiled code that won't update otherwise.

### Running the Application
```bash
laser_setup                    # Launch main GUI
laser_setup <procedure_name>   # Run specific procedure
laser_setup <script_name>      # Run specific script
python -m laser_setup          # Alternative launch method
```

### Development
```bash
pip install .[dev]             # Install with dev dependencies
flake8                         # Linting
```

## Architecture

### Configuration System (Hydra/OmegaConf)

The codebase uses a multi-layer YAML configuration system managed by `ConfigHandler`:

1. **Default configuration** (embedded in code via `AppConfig` dataclass)
2. **Global configuration** (path from default config or `CONFIG` environment variable)
3. **Local configuration** (path from global config)

Configuration files are located in `laser_setup/assets/templates/` (defaults) and user configs in `config/`:
- `config.yaml` - Main application settings (window size, paths, GUI settings)
- `instruments.yaml` - Instrument definitions and adapter settings
- `procedures.yaml` - Procedure-specific parameter overrides
- `sequences.yaml` - Sequence definitions grouping multiple procedures
- `parameters.yaml` - Global parameter configurations

The config loader uses `load_and_merge()` to merge these files into a single `CONFIG` object at runtime (`laser_setup/config/config.py`).

### Procedure System

All measurement procedures inherit from `BaseProcedure` (which extends PyMeasure's `Procedure`). Key aspects:

- **Parameters**: Use PyMeasure's parameter types (`Parameter`, `FloatParameter`, `IntegerParameter`, `BooleanParameter`, `ListParameter`) with custom `group_by` support for conditional visibility
- **INPUTS**: List of parameter names to display in the GUI
- **EXCLUDE**: Parameters to exclude from saved data files
- **DATA_COLUMNS**: Define output columns for measurements (first two columns are auto-plotted as X vs Y)
- **Lifecycle methods**:
  - `startup()`: Initialize instruments (calls `connect_instruments()` by default)
  - `execute()`: Main measurement logic (must be overridden, use `self.emit('results', dict)` to send data)
  - `shutdown()`: Cleanup (calls `instruments.shutdown_all()` by default)

The `@configurable` decorator allows procedures to be configured via YAML at class definition time using `configure_class()`.

**Key Procedures**:
- `IV`: I-V curves with voltage sweep, supports multiple sweep repetitions (`n_sweeps` parameter), saves time column
- `It`: Current vs time with laser ON/OFF cycling, includes `relax_time` parameter for post-cycle measurement
- `IVg`: Transfer curves (I vs gate voltage)
- `LaserCalibration`: Power meter calibration

### Instrument Management

`InstrumentManager` (laser_setup/instruments/manager.py) provides centralized instrument lifecycle management:

1. **Queue instruments** as class attributes using `InstrumentProxy`:
   ```python
   class MyProcedure(BaseProcedure):
       instruments = InstrumentManager()
       meter: Keithley2450 = instruments.queue(**Instruments.Keithley2450)
   ```

2. **Connect on demand** via `connect_all(self)` in `startup()` - replaces proxies with actual instrument instances

3. **Lazy loading**: Instruments are NOT instantiated at import time; they connect only when procedures use them

4. **Serial port detection**: Paths starting with `/dev/` or `COM` automatically use `SerialAdapter` with baudrate/timeout from kwargs

5. **Singleton pattern**: Instruments are cached by ID (`{class_name}/{adapter}`) and reused across procedure instances

6. **Debug mode**: Failed connections fall back to `DebugInstrument` (returns random data)

7. **Shutdown**: `shutdown_all()` safely closes all connections

8. **Disabling instruments**: Use `self.instruments.disable(self, 'instrument_name')` in `connect_instruments()` to skip certain instruments based on parameters

**Serial Instrument Configuration** (e.g., TENMA):
```yaml
TENMALASER:
  adapter: /dev/tty.usbmodem0002294704521  # macOS path
  # adapter: COM3  # Windows path
  IDN: TENMA 72-2715 V6.6 SN:37793899
  target: ${class:laser_setup.instruments.tenma.TENMA}
  kwargs:
    baudrate: 9600
    timeout: 2
```

### Sequence System

`Sequence` class (laser_setup/procedures/Sequence.py) chains multiple procedures:

- Defined in `sequences.yaml` with procedure names or inline configs
- Supports PyMeasure's `SequenceHandler` for parameter sweeps via `sequencer` key
- Each sequence creates a queue of procedure instances with merged configurations
- Executed via `SequenceWindow`
- Use `common_procedure` to define shared parameters across all procedures in sequence

Example sequence with parameter sweep:
```yaml
IVSweepVsd:
  name: IV Vsd Sweep (Vg OFF)
  description: Runs 8 IV measurements with varying Vsd
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

1. **MainWindow** (`laser_setup/display/windows/main_window.py`):
   - Entry point showing 4 main procedure buttons (IVg, It, IV, LaserCalibration)
   - Button colors: Blue (IVg), Green (It), Red (IV), Orange (LaserCalibration)
   - Menu bar provides access to all procedures, sequences, and scripts
   - Splash screen shows on startup (300x300px, 1 second minimum)

2. **ExperimentWindow**: Runs individual procedures with live plotting and parameter inputs

3. **SequenceWindow**: Executes procedure sequences with progress tracking

All windows are managed in `MainWindow.windows` dictionary to prevent duplicate instances.

**Important**: The `procedure_types` and `sequence_types` are stored early in `__init__` before `create_menu_bar()` pops them from the config dict.

### Configuration Registration

The `@configurable` decorator registers classes in specific config sections:
- `@configurable('procedures')` → registered in `CONFIG.procedures`
- `@configurable('sequences')` → registered in `CONFIG.sequences`

This enables dynamic instantiation via Hydra's `instantiate()` function.

### Patches

`laser_setup/patches.py` is imported first in `__init__.py` to monkey-patch PyMeasure classes before they're used elsewhere in the codebase.

## Important Patterns

1. **Parameter Override Flow**: `procedures.yaml` → `configure_class()` → `__init__()` → `override_parameters()` → `_apply_parameter_config()`

2. **Skip Flags**: `skip_startup` and `skip_shutdown` parameters wrap methods via `_wrap_skip()` to conditionally execute `connect_instruments()` or full startup/shutdown

3. **Instrument Proxy Pattern**: Delays instrument initialization until `connect_all()` is called, allowing configuration to happen before hardware access. This prevents crashes when instruments aren't connected.

4. **Type Hints**: `InstrumentProxy` uses `Generic[T]` to maintain type hints for IDE support while deferring instantiation

5. **Lazy Config Loading**: `Instruments` and `Parameters` in `procedures/utils.py` use lazy loading to prevent adapter instantiation at import time

6. **Time Columns**: When adding time data to procedures, place it as the 3rd column so default plots show the first two columns (typically voltage vs current)

## Common Modifications

### Adding a New Parameter to a Procedure

1. Import the parameter type: `from pymeasure.experiment import FloatParameter`
2. Add the parameter to the class: `my_param = FloatParameter('Description', units='V', default=1.0, minimum=0.0)`
3. Add to INPUTS list: `INPUTS = ParentClass.INPUTS + ['my_param']`
4. Use in `execute()`: `value = self.my_param`
5. **REBUILD**: `rm -rf build/ && pip install -e .`

### Changing Default Parameter Values

Edit `config/procedures.yaml`:
```yaml
ProcedureName:
  parameters:
    parameter_name:
      value: new_value
```

### Adding Time Column to Data

```python
# In procedure class
DATA_COLUMNS = ['X', 'Y', 't (s)']  # Time as 3rd column

# In execute()
start_time = time.time()
# ... during measurement loop ...
measurement_time = time.time() - start_time
self.emit('results', dict(zip(self.DATA_COLUMNS, [x, y, measurement_time])))
```

### Connecting Serial Instruments (TENMA, custom devices)

Serial instruments need explicit configuration in `instruments.yaml` with baudrate:
- Adapter string starting with `/dev/` (macOS/Linux) or `COM` (Windows)
- `kwargs` with `baudrate` and `timeout`
- No network calls are made during instrument config loading (lazy instantiation)

## Testing Without Hardware

The codebase includes `FakeProcedure` and `DebugInstrument` for testing. Use debug mode:
```bash
laser_setup -d  # or --debug
```

Failed instrument connections automatically fall back to `DebugInstrument` which returns random realistic data.

## Supported Instruments

- **Keithley 2450 SourceMeter** (VISA, USB)
- **Keithley 6517B Electrometer** (VISA)
- **TENMA Power Supply** (Serial: `/dev/tty.*` or `COMx`, 9600 baud)
- **Thorlabs PM100D Power Meter** (VISA, USB)
- **Bentham TLS120Xe Light Source** (Serial)
- **PT100SerialSensor** (Serial, custom)
- **Clicker** (Serial, custom temperature controller)
- All instruments from PyMeasure library

Instrument classes are in `laser_setup/instruments/`, each wrapping PyMeasure instrument classes or extending `Instrument` base class.

## Network Activity

**No external network calls** are made during normal operation. The previous `get_status_message()` call to an external API has been removed and now simply returns "Ready".

## Troubleshooting

1. **"No device found" error**: Check instrument is powered on, cables connected, and adapter address in `config/instruments.yaml` matches actual port (use `ls /dev/tty.*` on macOS/Linux or Device Manager on Windows)

2. **Program won't start**: Usually means an instrument adapter is failing at import time. Check recent config changes, ensure lazy loading is working.

3. **GUI changes not appearing**: Forgot to rebuild. Always run `rm -rf build/ && pip install -e .` after code changes.

4. **Parameter not showing in GUI**: Check it's in the INPUTS list and REBUILD.

5. **Splash screen issues**: Image is at `laser_setup/assets/img/splash.png`, scaled to 300x300px, displays for minimum 1 second.

## Version

Current version: `0.5.1-alpha` (defined in `laser_setup/__init__.py`)
