"""Dedicated settings dialog (KDE/TeXstudio-style) for the laser_setup application.

Provides a categorised sidebar + ParameterTree-per-section layout instead of
dumping the entire config tree into a single scrollable widget.
"""
from dataclasses import fields, is_dataclass
from typing import Any

from omegaconf import OmegaConf
from pyqtgraph.parametertree import Parameter, ParameterTree

from ...config import CONFIG, ConfigHandler
from ...config.defaults import AppConfig
from ..Qt import QtCore, QtGui, QtWidgets

# ---------------------------------------------------------------------------
# Pure helpers (no Qt needed)
# ---------------------------------------------------------------------------


def _navigate_dict(container: dict, path: tuple) -> Any:
    """Navigate a nested dict by a key-path tuple."""
    result = container
    for key in path:
        result = result[key]
    return result


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* (in-place, returns base)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _wrap_in_path(value: Any, path: tuple) -> dict:
    """Wrap *value* in a nested dict matching *path*."""
    result = value
    for key in reversed(path):
        result = {key: result}
    return result


def _extract_schema(dc: Any) -> dict:
    """Recursively build a schema dict from a dataclass instance."""
    schema: dict = {}
    if not is_dataclass(dc):
        return schema
    for f in fields(dc):
        schema[f.name] = {**f.metadata}
        value = getattr(dc, f.name, None)
        if is_dataclass(value):
            schema[f.name]["children"] = _extract_schema(value)
    return schema


def _get_parent_schema(schema_root: dict, path: tuple) -> dict:
    """Return ``{last_key: schema_entry}`` ready for use as *parent_schema* in
    :func:`_parameterize`.

    Navigates through 'children' dicts following *path[:-1]*, then returns the
    entry for *path[-1]*.
    """
    current = schema_root
    for key in path[:-1]:
        current = current.get(key, {}).get("children", {})
    last_key = path[-1]
    return {last_key: current.get(last_key, {})}


def _type_to_str(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


def _parameterize(
    key: str,
    obj: Any,
    schema: dict | None = None,
    skip_readonly: bool = True,
) -> dict | None:
    """Recursively convert a config value into a ParameterTree options dict.

    Returns *None* when the field is marked ``readonly: True`` in *schema* and
    *skip_readonly* is ``True`` (caller should filter ``None`` entries out).
    """
    param: dict = {"name": key}
    sub_schema: dict = {}
    if schema and key in schema:
        sub_schema = dict(schema[key])  # copy to avoid mutating caller's dict

    if skip_readonly and sub_schema.get("readonly", False):
        return None

    sub_schema_children = sub_schema.pop("children", {})
    param.update(sub_schema)

    if isinstance(obj, (dict, list)):
        param["type"] = "group"
        iterable = obj.items() if isinstance(obj, dict) else enumerate(obj)
        children = []
        for k, v in iterable:
            child = _parameterize(str(k), v, sub_schema_children, skip_readonly)
            if child is not None:
                children.append(child)
        param["children"] = children
    else:
        param["type"] = param.get("type", _type_to_str(obj))
        param["value"] = obj

    return param


def _extract_parameters(param: Parameter) -> Any:
    """Recursively convert a ParameterTree node back into a plain container."""
    ptype = param.opts.get("type", "group")
    if ptype == "group":
        # Group params have no scalar value — collect children instead
        value = {
            child.opts["name"]: _extract_parameters(child)
            for child in param.children()
        }
        # Integer-keyed children → sorted list (covers list parameters)
        if value and all(k.isdigit() for k in value.keys()):
            value = [value[k] for k in sorted(value.keys(), key=int)]
        return value
    value = param.value()
    if ptype == "font" and not isinstance(value, str):
        return value.family()
    return value


# ---------------------------------------------------------------------------
# Page definitions
# ---------------------------------------------------------------------------

# Each entry defines one sidebar category.
# 'sections' is a list of config-path tuples; multiple sections appear as
# sub-groups on the same page.
_SETTINGS_PAGES: list[dict] = [
    {
        "title": "Appearance",
        "sections": [("Qt", "GUI")],
        "description": "Visual style, fonts and theme",
    },
    {
        "title": "Main Window",
        "sections": [("Qt", "MainWindow")],
        "description": "Title, size and main-button configuration",
    },
    {
        "title": "Experiment Window",
        "sections": [("Qt", "ExperimentWindow")],
        "description": "Experiment window layout and behaviour",
    },
    {
        "title": "Sequence Window",
        "sections": [("Qt", "SequenceWindow")],
        "description": "Sequence window configuration",
    },
    {
        "title": "Files & Paths",
        "sections": [("Dir",), ("Filename",)],
        "description": "File paths and CSV output settings",
    },
    {
        "title": "Notifications",
        "sections": [("Telegram",)],
        "description": "Telegram bot token and chat IDs",
    },
    {
        "title": "Logging",
        "sections": [("Logging",)],
        "description": "Python logging configuration",
    },
    {
        "title": "Plot",
        "sections": [("matplotlib_rcParams",)],
        "description": "Matplotlib rc parameters",
    },
]


# ---------------------------------------------------------------------------
# SettingsPage
# ---------------------------------------------------------------------------


class SettingsPage(QtWidgets.QWidget):
    """A single category page that wraps one or more ParameterTree sections."""

    def __init__(
        self,
        sections: list[tuple],
        config_container: dict,
        schema_root: dict,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._sections = sections
        self._dirty = False
        self._root: Parameter | None = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tree = ParameterTree()
        layout.addWidget(self.tree)

        self._rebuild_tree(config_container, schema_root)
        # _dirty stays False — initial build is not a user change

    def _on_tree_changed(self, *_args) -> None:
        self._dirty = True

    def _rebuild_tree(self, config_container: dict, schema_root: dict) -> None:
        """(Re)build the ParameterTree from *config_container* using *schema_root*.

        Disconnects the old root's change signal before replacing it, and
        reconnects after, so the dirty flag is only set by genuine user edits.
        """
        # Disconnect stale signal before replacing root
        if self._root is not None:
            try:
                self._root.sigTreeStateChanged.disconnect(self._on_tree_changed)
            except Exception:
                pass

        if len(self._sections) == 1:
            path = self._sections[0]
            sub_config = _navigate_dict(config_container, path)
            parent_schema = _get_parent_schema(schema_root, path)
            opts = _parameterize(path[-1], sub_config, parent_schema, skip_readonly=True)
            if opts is None:
                opts = {"name": path[-1], "type": "group", "children": []}
            self._root = Parameter.create(**opts)
            self.tree.setParameters(self._root, showTop=False)
        else:
            children = []
            for path in self._sections:
                sub_config = _navigate_dict(config_container, path)
                parent_schema = _get_parent_schema(schema_root, path)
                opts = _parameterize(path[-1], sub_config, parent_schema, skip_readonly=True)
                if opts is None:
                    continue
                children.append(opts)
            self._root = Parameter.create(
                name="root", type="group", children=children
            )
            self.tree.setParameters(self._root, showTop=False)

        # Connect AFTER setParameters so the initial tree build doesn't set dirty
        self._root.sigTreeStateChanged.connect(self._on_tree_changed)

    def reset_to_defaults(self, default_container: dict, schema_root: dict) -> None:
        """Reload this page's tree from *default_container* (AppConfig defaults)."""
        self._rebuild_tree(default_container, schema_root)
        self._dirty = True  # Reset counts as a pending change

    def get_config_delta(self) -> dict:
        """Extract current values as a partial config dict suitable for
        :meth:`ConfigHandler.save_config`.
        """
        delta: dict = {}
        if len(self._sections) == 1:
            path = self._sections[0]
            extracted = _extract_parameters(self._root)
            _deep_merge(delta, _wrap_in_path(extracted, path))
        else:
            for i, path in enumerate(self._sections):
                children = list(self._root.children())
                if i >= len(children):
                    continue
                section_param = children[i]
                extracted = _extract_parameters(section_param)
                _deep_merge(delta, _wrap_in_path(extracted, path))
        return delta


# ---------------------------------------------------------------------------
# SettingsDialog
# ---------------------------------------------------------------------------

_SIDEBAR_WIDTH = 190


class SettingsDialog(QtWidgets.QDialog):
    """A KDE / TeXstudio-style settings dialog.

    Left sidebar lists categories; the right panel shows a :class:`SettingsPage`
    (ParameterTree) for the selected category.  Apply / OK / Cancel buttons sit
    at the bottom.
    """

    def __init__(
        self,
        config_handler: ConfigHandler,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config_handler = config_handler
        self.setWindowTitle("Settings")
        self.setMinimumSize(860, 560)
        self.resize(960, 640)
        self._pages: list[SettingsPage | QtWidgets.QWidget] = []
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 12)
        outer.setSpacing(0)

        # -- main splitter (sidebar | content) --------------------------
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter, stretch=1)

        # Sidebar -------------------------------------------------------
        sidebar = self._build_sidebar()
        splitter.addWidget(sidebar)

        # Content area --------------------------------------------------
        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 0)
        content_layout.setSpacing(8)

        self._page_title = QtWidgets.QLabel()
        title_font = self._page_title.font()
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        self._page_title.setFont(title_font)
        content_layout.addWidget(self._page_title)

        self._page_description = QtWidgets.QLabel()
        desc_font = self._page_description.font()
        desc_font.setPointSize(desc_font.pointSize() - 1)
        self._page_description.setFont(desc_font)
        self._page_description.setForegroundRole(QtGui.QPalette.ColorRole.Mid)
        content_layout.addWidget(self._page_description)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        content_layout.addWidget(sep)

        self._stack = QtWidgets.QStackedWidget()
        content_layout.addWidget(self._stack, stretch=1)

        splitter.addWidget(content)
        splitter.setSizes([_SIDEBAR_WIDTH, 700])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # Button bar ----------------------------------------------------
        btn_bar = self._build_button_bar()
        outer.addWidget(btn_bar)

        # Build pages ---------------------------------------------------
        self._build_pages()

        # Wire up sidebar selection
        self._category_list.currentRowChanged.connect(self._on_category_changed)
        self._category_list.setCurrentRow(0)

    def _build_sidebar(self) -> QtWidgets.QWidget:
        sidebar = QtWidgets.QWidget()
        sidebar.setObjectName("settings_sidebar")
        sidebar.setFixedWidth(_SIDEBAR_WIDTH)

        layout = QtWidgets.QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QtWidgets.QLabel("  Settings")
        header_font = header.font()
        header_font.setBold(True)
        header.setFont(header_font)
        header.setFixedHeight(36)
        header.setStyleSheet(
            "QLabel { border-bottom: 1px solid palette(mid); padding-left: 4px; }"
        )
        layout.addWidget(header)

        self._category_list = QtWidgets.QListWidget()
        self._category_list.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._category_list.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._category_list.setSpacing(1)
        self._category_list.setIconSize(QtCore.QSize(20, 20))
        self._category_list.setStyleSheet(
            """
            QListWidget {
                border: none;
                outline: none;
                background: transparent;
            }
            QListWidget::item {
                padding: 7px 10px;
                border-radius: 4px;
                margin: 1px 4px;
            }
            QListWidget::item:selected {
                background: palette(highlight);
                color: palette(highlighted-text);
            }
            QListWidget::item:hover:!selected {
                background: palette(midlight);
            }
            """
        )
        layout.addWidget(self._category_list)
        return sidebar

    def _build_button_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar_layout = QtWidgets.QHBoxLayout(bar)
        bar_layout.setContentsMargins(12, 8, 12, 0)

        btn_reset = QtWidgets.QPushButton("Reset Page to Defaults")
        btn_reset.setToolTip(
            "Restore all settings on this page to their built-in defaults.\n"
            "Nothing is saved until you press Apply or OK."
        )
        btn_reset.clicked.connect(self._on_reset_page)
        bar_layout.addWidget(btn_reset)

        bar_layout.addStretch()

        btn_apply = QtWidgets.QPushButton("Apply")
        btn_apply.setDefault(False)
        btn_apply.clicked.connect(self._on_apply)

        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QtWidgets.QPushButton("OK")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._on_ok)

        for btn in (btn_apply, btn_cancel, btn_ok):
            btn.setMinimumWidth(80)
            bar_layout.addWidget(btn)

        return bar

    def _build_pages(self) -> None:
        config_container = OmegaConf.to_container(CONFIG)
        config_container.pop("_session", None)
        data_dc = OmegaConf.to_object(CONFIG)
        schema_root = _extract_schema(data_dc)

        # Build and store the factory-default container for "Reset Page"
        _default_cfg = OmegaConf.structured(AppConfig, flags={"allow_objects": True})
        self._default_container: dict = OmegaConf.to_container(_default_cfg)
        self._default_container.pop("_session", None)
        self._schema_root: dict = schema_root

        style = self.style()

        # Map icon key strings to StandardPixmap enum values
        _icon_map: dict[str, QtWidgets.QStyle.StandardPixmap] = {
            "appearance": QtWidgets.QStyle.StandardPixmap.SP_DesktopIcon,
            "main window": QtWidgets.QStyle.StandardPixmap.SP_TitleBarNormalButton,
            "experiment window": QtWidgets.QStyle.StandardPixmap.SP_CommandLink,
            "sequence window": QtWidgets.QStyle.StandardPixmap.SP_MediaSeekForward,
            "files & paths": QtWidgets.QStyle.StandardPixmap.SP_DirIcon,
            "notifications": QtWidgets.QStyle.StandardPixmap.SP_MessageBoxInformation,
            "logging": QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView,
            "plot": QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView,
        }

        for page_def in _SETTINGS_PAGES:
            title: str = page_def["title"]
            description: str = page_def.get("description", "")
            sections: list[tuple] = page_def["sections"]

            # -- Sidebar item --
            item = QtWidgets.QListWidgetItem(title)
            sp = _icon_map.get(title.lower())
            if sp is not None:
                item.setIcon(style.standardIcon(sp))
            item.setData(QtCore.Qt.ItemDataRole.UserRole, description)
            self._category_list.addItem(item)

            # -- Settings page --
            try:
                page = SettingsPage(sections, config_container, schema_root, parent=self)
            except Exception as exc:
                page = QtWidgets.QWidget()
                lbl = QtWidgets.QLabel(f"Could not load page:\n{exc}")
                lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                QtWidgets.QVBoxLayout(page).addWidget(lbl)

            self._pages.append(page)
            self._stack.addWidget(page)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_category_changed(self, row: int) -> None:
        if not (0 <= row < len(_SETTINGS_PAGES)):
            return
        page_def = _SETTINGS_PAGES[row]
        self._page_title.setText(page_def["title"])
        self._page_description.setText(page_def.get("description", ""))
        self._stack.setCurrentIndex(row)

    def _on_reset_page(self) -> None:
        """Reset the currently visible page to built-in AppConfig defaults."""
        row = self._category_list.currentRow()
        if not (0 <= row < len(self._pages)):
            return
        page = self._pages[row]
        if not isinstance(page, SettingsPage):
            return
        title = _SETTINGS_PAGES[row]["title"]
        answer = QtWidgets.QMessageBox.question(
            self,
            "Reset to defaults",
            f"Reset <b>{title}</b> to built-in defaults?<br><br>"
            "This only updates the form — nothing is saved until you press Apply or OK.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            page.reset_to_defaults(self._default_container, self._schema_root)

    def _on_apply(self) -> None:
        dirty_pages = [p for p in self._pages if isinstance(p, SettingsPage) and p._dirty]
        if not dirty_pages:
            QtWidgets.QMessageBox.information(self, "Nothing to save", "No settings were changed.")
            return
        delta: dict = {}
        for page in dirty_pages:
            _deep_merge(delta, page.get_config_delta())
        try:
            self._config_handler.save_config(delta)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save error", str(exc))
            return
        for page in dirty_pages:
            page._dirty = False

        # Apply appearance changes live
        gui_delta = delta.get('Qt', {}).get('GUI', {})

        theme_mode_val = gui_delta.get('theme_mode')
        if theme_mode_val:
            from ..theme import ThemeMode
            from ..theme import manager as _theme_manager
            try:
                _theme_manager().set_mode(ThemeMode[theme_mode_val])
            except (KeyError, Exception):
                pass

        font_family = gui_delta.get('font')
        font_size = gui_delta.get('font_size')
        if font_family is not None or font_size is not None:
            app = QtWidgets.QApplication.instance()
            if app is not None:
                font = app.font()
                if font_family:
                    font.setFamily(font_family)
                if font_size is not None:
                    font.setPointSize(int(font_size))
                app.setFont(font)

        QtWidgets.QMessageBox.information(self, "Saved", "Settings saved successfully.")

    def _on_ok(self) -> None:
        self._on_apply()
        self.accept()
