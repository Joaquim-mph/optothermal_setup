# Repository Guidelines

## Project Structure & Module Organization
The core package lives in `laser_setup/`. GUI windows sit in `laser_setup/display/`, instrument drivers in `laser_setup/instruments/`, and reusable procedures in `laser_setup/procedures/`. Hydra/OmegaConf templates live under `laser_setup/assets/templates/`, with runtime defaults in `laser_setup/config/`. Automated tests reside in `tests/`, and hardware smoke scripts such as `test_tenma.py` live at the project root.

## Build, Test, and Development Commands
Create a virtual environment, then install dependencies locally:
```bash
pip install -e .
# or: uv pip install --editable .
```
Launch the GUI with either `laser_setup` or `python -m laser_setup`. Run the automated suite with `pytest tests`; focus on a device workflow via `pytest tests/test_tenma.py -k tenma`. Lint before submitting changes using `flake8 laser_setup tests`.

## Coding Style & Naming Conventions
Follow PEP 8: four-space indentation, lower_snake_case for functions and modules, UpperCamelCase for classes, caps for module-level constants. Keep configuration filenames and Hydra node names aligned (`procedures.yaml` → `laser_setup.procedures.*`) so dynamic loading stays predictable. Run `flake8` for formatting feedback; optional static checks with `pyright` are available if you want stricter typing locally.

## Testing Guidelines
Use `pytest` with files named `test_*.py` that mirror module paths (e.g., tests for `laser_setup/instruments/manager.py` belong in `tests/instruments/test_manager.py`). Mock hardware interactions whenever NI-VISA devices are unavailable, and gate long-running cases with descriptive `-k` selectors. Exercise both GUI orchestration and instrument handshakes; add regression cases whenever you touch YAML schemas or procedure lifecycles.

## Commit & Pull Request Guidelines
Current history mixes punchy imperatives (`Fix syntax in VVg`) with informal notes (`sorry benja :(`); normalize on short, present-tense summaries under ~50 characters plus optional body details. Reference related issues in the body with `Fixes #123` when applicable. PRs should cover the change intent, configuration or hardware prerequisites, screenshots/gifs for GUI updates, and smoke-test highlights. Request review from collaborators responsible for the affected instruments or procedures.

## Configuration Tips
When introducing new instruments or procedures, duplicate the relevant YAML template under `laser_setup/assets/templates/`, adjust `_target_` entries to your module path, and confirm the entry loads via `laser_setup <name>`. Keep credentials and instrument addresses out of version control—prefer local Hydra overrides or private config files ignored by git.
