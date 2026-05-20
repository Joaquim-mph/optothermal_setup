# Investigation: Sample deaths and Keithley USB crashes during `It`

**Date:** 2026-05-20
**Status:** Root cause identified (software regression) + open hardware factors
**Affected procedure:** `It` (I vs t, with laser cycling). Believed possible in any procedure, but only observed during `It`.

---

## TL;DR

Few-layer-graphene samples were destroyed (contacts physically blown apart, "mini
explosion" under the microscope) during `It` runs, each time coinciding with the
Keithley 2450 dropping off USB (`USBError` → endpoint stall) that required a
**physical power cycle** of the instrument to recover.

Two distinct problems were found:

1. **Software regression (the thing we can fix in code).** Upstream
   (`nanolab-fcfm/laser_setup`) de-energized the sample after **every** procedure
   (gate ramped to 0 V, supply outputs off, Keithley source disabled). This fork
   stopped doing that — to avoid USB `resource busy` errors — and now leaves the
   sample **continuously biased** between runs. This is the single behavioral
   difference, on identical hardware, between "never failed" (upstream) and
   "fails" (this fork).

2. **Hardware factor (bench-side, not fixable in code).** The physical energy
   that blows a contact cannot come from the measurement setpoints (they are far
   too small — see [Energy budget](#energy-budget)). A fast destructive transient
   reaches the source–drain contact, and the same transient crashes the Keithley's
   USBTMC link. Mitigation is electrical (grounding, gate current limiting, USB
   isolation), not software.

The planned software fix restores upstream's per-run de-energization **without**
reintroducing the USB `resource busy` problem.

---

## Symptoms

- Sample dies during an `It` run. Post-mortem (microscope): the few-layer graphene
  in contact with the gold pads is destroyed — looks like a localized explosion.
- Simultaneously, the Keithley 2450 throws `usb.core.USBError [Errno 5] Input/Output
  Error` → `[Errno 32] Pipe error` (USBTMC bulk endpoint stall).
- After the crash, the device could **not** be re-connected by unplugging/replugging
  the USB cable. Only powering the Keithley off and on restored communication.
- Recurring: observed 3×, with 2 confirmed sample deaths. Always during `It`
  (which does not prove it is `It`-exclusive).
- Nothing physically moved in the lab at the moment of failure.

---

## Evidence

### Failure always lands in the laser-ON window, ~30 s after switch-on

Pulling the tail of every `It` run that terminated early (full run = 180 s for a
120 s laser period):

| Run | ended at | relative to laser-ON | tail current | laser_v | VG |
|---|---|---|---|---|---|
| 15_1  | 90.4 s  | +30 s | 20.7 µA flat | 0.91 V | −0.7 V |
| 15_3  | 90.9 s  | +31 s | 30 µA flat   | 1.67 V | −0.9 V |
| 15_5  | 101.9 s | +42 s | 26 µA flat   | 3.22 V | −0.9 V |
| 15_24 | 96.4 s  | +36 s | 20 µA flat   | 4.01 V | −0.5 V |
| 20_11 | 86.2 s  | +26 s | 53 µA flat   | 4.25 V | −0.5 V (confirmed death) |

Observations:
- Every early termination with the laser ON lands **26–42 s into the laser-ON
  plateau** — never during the 60 s dark baseline, never at the switch-on edge.
- Current is **flat and normal on the last good sample** every time (no runaway,
  no climb toward compliance — no electrical precursor in the measured signal).
- A run at **VG = +40 V with the laser OFF survived** — high gate voltage in the
  dark was fine; sub-volt gate *with light* killed it.

This rules out: laser switching transient (the edge is 30 s earlier and harmless),
gradual Joule/current overstress (no precursor), and the gate dielectric as the
*visible* failure (damage is at the S/D contact, and the user confirmed gate
breakdown looks different).

### Energy budget

At the setpoints used during the deaths, no connected source can explode a contact:

| Source | Setpoint | Max power available |
|---|---|---|
| Keithley S/D | 0.1 V, 1.1 mA compliance | ~0.1 mW (current-limited) |
| Gate TENMA | −0.5 V, ~50 mA limit | ~25 mW worst case |
| Laser at sample | ~µW (fiber-delivered, electrically isolated) | negligible |

Physically blowing few-layer graphene needs on the order of **millijoules in
microseconds**. None of the steady setpoints can deliver that. Therefore the
destructive energy was a **transient** that briefly drove a node far past its
setpoint (or stored energy discharging), **not** the steady bias. For reference, a
~2 nF stray capacitance (a couple of metres of coax, or a modest floating plate)
charged to ~1 kV stores ~1 mJ — the scale of an ESD/arc event, which also explains
the simultaneous USBTMC crash.

The laser is fiber-coupled, so its only role is delivering **light**: it is a
*trigger/enabler* (photo-weakening the contact over ~30 s of illumination), not the
energy source.

---

## Root cause: lost per-run de-energization (software regression)

Diffing this fork against `upstream/main` (fork point: `ef787b5`, v0.6.0-alpha):

- `It.py` is **functionally identical** to upstream (its diff is pure
  black-formatting). The electrical sequence run during every death is upstream's.
- `keithley.py` and `tenma.py` are **unchanged**.
- The only behavioral change to the per-run lifecycle is in
  `BaseProcedure.shutdown()`:

**Upstream** — de-energizes after *every* procedure:
```python
def shutdown(self):
    self.instruments.shutdown_all()   # TENMA -> 0 V then output off;
                                      # Keithley source off; connection closed
```

**This fork** — no-op on normal completion; safety reset only on abort/FAILED:
```python
def shutdown(self):
    # Keep instruments cached for reuse (avoids USB "resource busy")
    log.debug("Keeping instruments connected for reuse in next experiment")
```

**Consequence:** the sample is now held under gate + drain bias **continuously
across an entire session** — through every idle gap and across dozens of runs —
instead of being returned to 0 V / outputs-off after each run. Upstream gave the
device a de-biased rest between every measurement; this fork never does.

That is the single difference between the "never failed" and "fails" configurations
on identical hardware. Continuous bias (with periodic illumination) is exactly the
condition for cumulative contact/oxide degradation that ends in a sudden,
destructive failure — with the laser providing the per-run trigger.

> **Honesty about the proof:** the diff *proves* the behavioral regression (no
> de-energization between runs). It does **not** prove this is the exact death
> mechanism — the energy/transient argument above still applies at the instant of
> failure. But it is the only behavioral difference between the two configurations,
> which makes it the strongest available lead, and the fix is low-risk regardless.

### Why replug didn't recover the Keithley, but a power cycle did

Two independent wedge layers:

- **Device side:** the transient halted the Keithley's USBTMC bulk endpoint (and
  likely hung its USB controller). Unplugging the cable does **not** power down the
  instrument, so its hung USB firmware state persists across a replug. Only a
  **power cycle** resets the instrument's USB controller.
- **Host side:** `InstrumentManager` caches the connection and **never releases the
  USB interface on error** (eviction only happens at app exit). The stale libusb
  interface claim → `[Errno 16] resource busy` on the next attempt → an **app
  restart** was needed to clear the host side. Upstream's close/reopen-every-run
  released the interface automatically, which is why upstream recovered more
  gracefully.

---

## Fixes

### Software (implemented / planned — restores upstream behavior safely)

1. **Safe-state on every shutdown.** Run the safety reset (ramp TENMAs to 0 V →
   output **off**, disable Keithley source) on **normal completion** too, not only
   on abort/FAILED — i.e. replicate upstream's `shutdown_all()` *electrical* effect,
   but **keep the connection cached** (no close/evict). This reverts the regression
   without bringing back `resource busy`.
2. **Evict + release only on `status == FAILED`.** On a genuine comms error, close
   and evict the cached instrument so the USB interface frees without an app
   restart. Do **not** evict on a clean/manual stop (keep it cached).
3. **`TENMA.ramp_to_voltage` read-safety.** Coerce the voltage read to `float`
   (it has been observed returning a `str`, raising `TypeError` and silently
   skipping the laser-TENMA reset on abort).
4. **Default to outputs off between runs.** Upstream did `ramp to 0 → output off`
   every run and never had the problem, so output-off is the proven-safe baseline.

### Hardware / bench (NOT fixable in code — the destructive transient)

The energy budget shows the killer is a transient, not the measurement. Recommended
on the bench, in priority order:

1. **Series resistor in the gate line (100 kΩ–1 MΩ).** The gate is capacitive
   (DC gate current ~nA), so a series R is invisible to the measurement but caps any
   fault current the gate can ever deliver (a 60 V spike through 1 MΩ = 60 µA —
   incapable of exploding anything). Cheapest, highest-value protection.
2. **Series R + clamp (TVS/Schottky) on the S/D lines** to bound transients.
3. **USB galvanic isolator** on the Keithley (e.g. ADuM4160-class) + ferrites —
   keeps ground transients off the PC and shields the Keithley's USB controller;
   likely prevents the wedge entirely.
4. **Star-ground** the sample stage, probe bodies, and cable shields; eliminate
   floating conductors near the sample.
5. Log **bench humidity** — ESD accumulation is worse in dry air.

### Not the cause (ruled out)

- **Compliance current.** At 0.1 V × 1.1 mA = 0.1 mW the Keithley cannot blow a
  contact; lowering compliance would not have prevented this death. (Tightening
  `Irange` to match the ~50 µA operating current is still good practice for
  signal resolution and fault headroom, but it is not the fix here.)
- **Laser switching transient / laser power / laser wiring.** Fiber-coupled and
  electrically isolated; switching edge is harmless; power is µW.

---

## Open questions

- Exact physical mechanism of the destructive transient (gate-TENMA glitch vs an
  external ESD/mains transient that only kills when the contact is photo-weakened).
  Resolve with the dummy-load + beam-blocked experiments below.
- Whether the failure is truly `It`-exclusive or just most-observed there (longest
  dwell + laser on).

### Diagnostic experiments (cost no sample)

1. `It`, laser ON, ≥4 V, full duration, **dummy resistor (~1–2 kΩ) in place of the
   sample**, repeated. If the USB still crashes ~30 s in → the event is independent
   of the precious sample (instrument/ground), safe to iterate. Check if the dummy
   resistor itself shows damage.
2. Then drive the laser but **block the beam / disconnect the diode optically**.
   Still crashes → electrical/ground. Needs the beam on the sample → photo effect
   at the device.
3. **Scope the gate line** (and S/D) during a laser-on `It` on the dummy — a
   transient ~30 s in is the direct catch that turns this from hypothesis to fact.

---

## References

- Fork point vs upstream: `git merge-base upstream/main HEAD` → `ef787b5`
- Key files: `laser_setup/procedures/BaseProcedure.py`,
  `laser_setup/instruments/manager.py`, `laser_setup/instruments/tenma.py`,
  `laser_setup/procedures/It.py`
- Data analyzed: `data/2026-05-15/`, `data/2026-05-18/`, `data/2026-05-20/` (`It*.csv`)
