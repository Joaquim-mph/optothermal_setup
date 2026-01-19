# Sequences

This document explains how `Sequence` works, how it is configured, and how to
build a complete sequence from scratch.

## What a Sequence is
A `Sequence` is a configuration-driven container that queues multiple PyMeasure
`Procedure` instances to run in order. It is not a `Procedure` itself, but the
GUI runs each step in an `ExperimentWindow` and tracks overall progress in the
`SequenceWindow`.

Key references:
- `laser_setup/procedures/Sequence.py` (Sequence class)
- `config/sequences.yaml` (user-editable sequences)
- `laser_setup/config/templates/sequences.yaml` (template)

## How the YAML is resolved
Sequences are defined under `config/sequences.yaml` (or a custom
`sequences_file`), then Hydra resolves them into `Sequence` classes at runtime.
The `@configurable('sequences')` decorator connects the YAML definitions to the
`Sequence` class.

The GUI menus are populated from the `_types` mapping at the bottom of the YAML
file. If a sequence is not in `_types`, it will not show up in the Sequences
menu.

## Core YAML fields
Each sequence entry typically includes:
- `name`: Display name shown in the GUI.
- `description`: Short human-readable description.
- `common_procedure`: Base procedure class whose parameters are shared across
  all steps (usually `ChipProcedure`).
- `inputs_ignored`: Parameter names to hide from the shared inputs.
- `procedures`: Ordered list of steps to run. Each item is either:
  - A procedure name string (e.g., `IVg`), or
  - A mapping `{ProcedureName: config}` where `config` is passed to the
    procedure constructor.

### Per-procedure overrides
Use `parameters` inside a procedure config to override per-step defaults:
```yaml
- IVg:
    parameters:
      vg_start: {value: -20.0}
      vg_end: {value: 20.0}
```

### Sequencer expansion
If a procedure config includes `sequencer`, the sequencer string is parsed by
`pymeasure.experiment.sequencer.SequenceHandler`. Each generated parameter set
becomes a separate procedure instance in the queue.
```yaml
- It:
    sequencer: |-
      - "target_T", "arange(35., 71., 5)"
    parameters:
      laser_T: {value: 1000.0}
```

## Worked end-to-end example
This example builds a full sequence from scratch that:
1) Runs an initial `IVg` sweep,
2) Waits 5 seconds,
3) Runs an `It` transient for multiple temperatures,
4) Finishes with another `IVg` sweep.

1) Add a new sequence to `config/sequences.yaml`:
```yaml
ThermalSweepSequence:
  name: Thermal Sweep Sequence
  description: IVg, wait, It across target_T, IVg
  common_procedure: ${class:laser_setup.procedures.ChipProcedure}
  inputs_ignored: ['show_more', 'skip_startup', 'skip_shutdown']
  procedures:
    - IVg:
        parameters:
          vg_start: {value: -30.0}
          vg_end: {value: 30.0}
          vds: {value: 0.75}
    - Wait:
        parameters:
          wait_time: {value: 5.0}
    - It:
        sequencer: |-
          - "target_T", "arange(30., 61., 10)"
        parameters:
          laser_T: {value: 1000.0}
          vg: {value: "40."}
          vds: {value: 0.75}
          skip_startup: {value: true}
          skip_shutdown: {value: true}
    - IVg:
        parameters:
          vg_start: {value: -30.0}
          vg_end: {value: 30.0}
          vds: {value: 0.75}
```

2) Add it to the `_types` list so it shows in the GUI menu:
```yaml
_types:
  MainSequence: ${sequence:MainSequence}
  TestSequence: ${sequence:TestSequence}
  ItMadness: ${sequence:ItMadness}
  ThermalSweepSequence: ${sequence:ThermalSweepSequence}
```

3) Reload the GUI (or restart `laser_setup`).

4) Open the sequence from the Sequences menu. The shared inputs are taken from
`common_procedure` (minus `inputs_ignored`), and per-step overrides are applied
when each step is launched.

## Tips and gotchas
- If a procedure name is not present in `config/procedures.yaml`, Sequence will
  skip it with a warning.
- `sequencer` overrides are applied before the procedure is instantiated, so
  they can safely set `parameters` values for each iteration.
- If a parameter should be shared across all steps, prefer putting it into the
  shared UI inputs (from `common_procedure`) instead of repeating it in every
  step config.
