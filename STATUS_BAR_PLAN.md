# Status Bar Redesign Plan — ExperimentWindow

**File:** `laser_setup/display/windows/experiment_window.py`

---

## Goal

Reduce crowding in the status bar during runs by: merging redundant items,
relocating contextual info to better homes, and replacing the verbose file-path
label with a compact folder-open button.

---

## Current layout (during a run)

```
LEFT ──────────────────────────────────────────────────── RIGHT
[ Running: IVg ][ ====75%==== ][ 03m 42s ][ I_ds = 12 µA ]   [Run Browser ▼][Save Plot][ → data/2026-02-25/IVg… ]
```

Problems:
- "Running: IVg" (label) + progress bar are **redundant** — both say "running".
- Four left-side widgets all visible at once is cramped.
- The file-path label is long and fights the right-side buttons for space.
- The elapsed timer is secondary info but sits in the primary (left) zone.

---

## Planned changes

### 1 · Merge Run Status Label into the Progress Bar text

**What:** Remove the separate `_run_status_label` widget.
**How:**
- At idle: hide the progress bar, show nothing (status bar is blank on the left — clean).
- On queue: set progress bar format to `"Queued: {name} (+N more)"`, show bar at 0 %.
- On run start: set format to `"Running: {name}  %p%"`, show bar.
- On finish/abort/fail: hide bar, reset format to `"%p%"`. The existing
  `showMessage(...)` flash ("Finished: …", "Aborted…", "Failed…") already handles
  post-run feedback.

**Lines affected:** 146–148 (label creation), 314 (`_on_exp_queued`),
317–318 (`_on_exp_running`), 401–403 / 411–412 / 420–421 (idle resets).

**Progress bar sizing:** Drop `setFixedWidth(150)` (line 152); let it size
naturally. Add `self._status_bar.addWidget(self._run_progress_bar, 1)` with
stretch=1 so it expands to fill available left-side space.

---

### 2 · Move Elapsed Timer to the right side

**What:** Change `addWidget` → `addPermanentWidget` for `_elapsed_label`.
**How:** Move its `addWidget` call (line 161) to after `_save_plot_btn` is added,
using `addPermanentWidget`. Insert it between `_save_plot_btn` and
`_browser_toggle` so the order (right→left) is:

```
[Run Browser ▼]  [Save Plot]  [03m 42s]  [📁]
```

No logic changes needed — show/hide and tick timer stay the same.

---

### 3 · Move Last Value to the plot as a TextItem overlay

**What:** Remove `_last_value_label` from the status bar entirely.
**How:**
- In `__init__`, after plot setup, create a `pg.TextItem` anchored to the
  top-right corner of the plot:
  ```python
  self._last_value_item = pg.TextItem(anchor=(1, 0))
  self._last_value_item.setParentItem(self.plot_widget.plot_frame.plot.getViewBox())
  self._last_value_item.hide()
  ```
- In `_on_plot_updated`, set `self._last_value_item.setText(...)` and position it
  at the top-right of the current view range instead of updating `_last_value_label`.
- In `_stop_last_value`, call `self._last_value_item.hide()` instead of hiding
  the label.
- Color the TextItem to match the theme; connect `_on_theme_changed` to update it.

**Lines affected:** 167–170 (remove label creation), 361–378 (`_on_plot_updated`
rewrite), 353–359 (`_stop_last_value` rewrite).

---

### 4 · Replace File Path Label with an "Open Folder" icon button

**What:** Remove `_file_path_label` (lines 192–197). Add `_open_folder_btn`, a
`QToolButton` with a standard folder-open icon, hidden until an experiment
completes.

**How:**
```python
self._open_folder_btn = QtWidgets.QToolButton()
self._open_folder_btn.setIcon(
    self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon)
)
self._open_folder_btn.setToolTip('Open folder where last experiment was saved')
self._open_folder_btn.setStyleSheet('QToolButton { border: none; padding: 2px 6px; }')
self._open_folder_btn.clicked.connect(self._reveal_last_folder)
self._open_folder_btn.hide()
self._status_bar.addPermanentWidget(self._open_folder_btn)
```

Add a helper that uses the already-stored `self._last_filename`:
```python
def _reveal_last_folder(self) -> None:
    path = getattr(self, '_last_filename', None)
    if path:
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(os.path.dirname(os.path.abspath(path)))
        )
```

In `_show_file_path` (line 426), replace `_file_path_label` logic with simply
`self._open_folder_btn.show()`.

The existing `_reveal_file(self, path)` method (lines 438–441) can be kept or
removed — its functionality is now fully covered by `_reveal_last_folder`.

---

### 5 · Hide Save Plot button until first experiment is queued

**What:** Call `self._save_plot_btn.hide()` after creating it (line 190).
**How:** In `_on_exp_queued`, show it:
```python
self._save_plot_btn.show()
```
Once shown, it stays visible for the rest of the session (no need to re-hide).

---

## Final layout

```
IDLE:
  LEFT: (empty)                                RIGHT: [Run Browser ▼]

QUEUED:
  LEFT: [ Queued: IVg (+1 more)  0% ·······]  RIGHT: [Run Browser ▼][Save Plot]

RUNNING:
  LEFT: [ Running: IVg  75% ================]  RIGHT: [Run Browser ▼][Save Plot][03m 42s]
         + "I_ds = 12.34 µA" TextItem in plot top-right corner

POST-RUN (Finished/Aborted/Failed flash message via showMessage):
  LEFT: (empty)                                RIGHT: [Run Browser ▼][Save Plot][00m 48s][📁]
```

---

## Order of implementation

1. Merge status label into progress bar text + stretch (changes 1).
2. Move elapsed timer to right side (change 2).
3. Add `_open_folder_btn`, remove `_file_path_label` (change 4).
4. Hide Save Plot until first queue (change 5).
5. Move Last Value to plot TextItem (change 3) — most involved, do last.

---

## No other files need changes.

All modifications are self-contained within `experiment_window.py`.
