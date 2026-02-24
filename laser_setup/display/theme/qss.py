"""QSS (Qt Style Sheet) generator functions.

Provides named style generators that produce QSS strings based on
current theme colors.
"""

from .manager import manager


def qss(style_name: str) -> str:
    """Get a QSS style string by name.

    Args:
        style_name: Name of the style (e.g., 'button_primary', 'card')

    Returns:
        QSS string for the requested style

    Raises:
        ValueError: If style name is not recognized
    """
    generators = {
        # Buttons
        'button_primary': _button_primary,
        'button_secondary': _button_secondary,
        'button_danger': _button_danger,
        'button_success': _button_success,

        # Procedure buttons
        'button_proc_ivg': _button_proc_ivg,
        'button_proc_it': _button_proc_it,
        'button_proc_iv': _button_proc_iv,
        'button_proc_laser': _button_proc_laser,

        # Cards and panels
        'card': _card,
        'card_hover': _card_hover,

        # Labels
        'label_primary': _label_primary,
        'label_secondary': _label_secondary,
        'label_info': _label_info,

        # Inputs
        'input': _input,
        'scroll_area': _scroll_area,
    }

    if style_name not in generators:
        raise ValueError(f"Unknown style: {style_name}. Available: {list(generators.keys())}")

    return generators[style_name]()


def _button_primary() -> str:
    """Primary action button style."""
    c = manager().colors
    return f"""
        QPushButton {{
            background-color: {c.blue};
            color: #FFFFFF;
            padding: 8px 20px;
            border: none;
            border-radius: 4px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {c.blue_hover};
        }}
        QPushButton:pressed {{
            background-color: {c.blue_hover};
            padding-top: 10px;
            padding-bottom: 6px;
        }}
        QPushButton:disabled {{
            background-color: {c.comment};
            color: {c.bg_highlight};
        }}
    """


def _button_secondary() -> str:
    """Secondary/neutral button style."""
    c = manager().colors
    return f"""
        QPushButton {{
            background-color: {c.bg_highlight};
            color: {c.fg};
            padding: 8px 16px;
            border: 1px solid {c.border};
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {c.border};
            border-color: {c.blue};
        }}
        QPushButton:pressed {{
            background-color: {c.border};
        }}
    """


def _button_danger() -> str:
    """Danger/delete button style."""
    c = manager().colors
    return f"""
        QPushButton {{
            background-color: {c.red};
            color: #FFFFFF;
            border: none;
            border-radius: 3px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {c.red_hover};
        }}
        QPushButton:pressed {{
            background-color: {c.red_hover};
        }}
    """


def _button_success() -> str:
    """Success/confirm button style."""
    c = manager().colors
    return f"""
        QPushButton {{
            background-color: {c.green};
            color: #FFFFFF;
            padding: 8px 20px;
            border: none;
            border-radius: 4px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {c.green_hover};
        }}
    """


def _button_proc_ivg() -> str:
    """IVg procedure button (blue)."""
    c = manager().colors
    return _proc_button_template(c.proc_ivg, c.proc_ivg_hover)


def _button_proc_it() -> str:
    """It procedure button (green)."""
    c = manager().colors
    return _proc_button_template(c.proc_it, c.proc_it_hover)


def _button_proc_iv() -> str:
    """IV procedure button (red)."""
    c = manager().colors
    return _proc_button_template(c.proc_iv, c.proc_iv_hover)


def _button_proc_laser() -> str:
    """Laser procedure button (orange)."""
    c = manager().colors
    return _proc_button_template(c.proc_laser, c.proc_laser_hover)


def _proc_button_template(bg: str, hover: str) -> str:
    """Template for procedure buttons."""
    return f"""
        QPushButton {{
            font-size: 16px;
            font-weight: 600;
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            background-color: {bg};
            padding: 10px;
        }}
        QPushButton:hover {{
            background-color: {hover};
            font-size: 17px;
        }}
        QPushButton:pressed {{
            background-color: {hover};
            padding-top: 12px;
            padding-bottom: 8px;
        }}
    """


def _card() -> str:
    """Card/panel container style."""
    c = manager().colors
    return f"""
        QFrame {{
            background-color: {c.bg_sidebar};
            border: 1px solid {c.border};
            border-radius: 5px;
        }}
        QFrame:hover {{
            border-color: {c.blue};
            border-width: 2px;
        }}
        QLabel {{
            color: {c.fg};
            background-color: transparent;
            border: none;
        }}
        QToolButton {{
            color: {c.fg};
            background-color: transparent;
            border: none;
        }}
    """


def _card_hover() -> str:
    """Card style with active hover state."""
    c = manager().colors
    return f"""
        QFrame {{
            background-color: {c.bg_sidebar};
            border: 2px solid {c.blue};
            border-radius: 5px;
        }}
        QLabel {{
            color: {c.fg};
            background-color: transparent;
            border: none;
        }}
    """


def _label_primary() -> str:
    """Primary label style."""
    c = manager().colors
    return f"color: {c.fg};"


def _label_secondary() -> str:
    """Secondary/subdued label style."""
    c = manager().colors
    return f"color: {c.fg_dark};"


def _label_info() -> str:
    """Info/accent colored label style."""
    c = manager().colors
    return f"color: {c.blue}; font-style: italic;"


def _input() -> str:
    """Input field style (line edit, combo box)."""
    c = manager().colors
    return f"""
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            background-color: {c.bg_highlight};
            color: {c.fg};
            border: 1px solid {c.border};
            border-radius: 3px;
            padding: 4px 8px;
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {c.blue};
            border-width: 2px;
        }}
    """


def _scroll_area() -> str:
    """Scroll area style for sequence builder."""
    c = manager().colors
    return f"""
        QScrollArea {{
            border: 2px dashed {c.border};
            border-radius: 8px;
            background-color: {c.bg_sidebar};
        }}
    """


# Per-procedure color palette: (light_bg, light_hover, dark_bg, dark_hover)
_PROC_PALETTE = [
    ("#2563EB", "#1D4ED8", "#4A90E2", "#60A5FA"),  # Blue    (IVg)
    ("#16A34A", "#15803D", "#22C55E", "#4ADE80"),  # Green   (It)
    ("#DC2626", "#B91C1C", "#EF4444", "#F87171"),  # Red     (IV)
    ("#D97706", "#B45309", "#F59E0B", "#FBBF24"),  # Orange  (LaserCalibration)
    ("#7C3AED", "#6D28D9", "#8B5CF6", "#A78BFA"),  # Purple
    ("#0891B2", "#0E7490", "#06B6D4", "#22D3EE"),  # Cyan
    ("#BE185D", "#9D174D", "#EC4899", "#F472B6"),  # Pink
    ("#065F46", "#047857", "#10B981", "#34D399"),  # Teal
]

# Well-known procedures get a fixed palette slot regardless of their button position
_PROC_FIXED_INDEX: dict[str, int] = {
    'IVg': 0,           # Blue
    'It': 1,            # Green
    'IV': 2,            # Red
    'LaserCalibration': 3,  # Orange
    'VVg': 4,           # Purple
    'Vt': 5,            # Cyan
}


# Slot index → (color_key, hover_key)
_SLOT_COLORS = [
    ("blue",    "blue_hover"),    # 0
    ("green",   "green_hover"),   # 1
    ("red",     "red_hover"),     # 2
    ("orange",  "orange_hover"),  # 3
    ("magenta", "magenta_hover"), # 4
    ("cyan",    "cyan_hover"),    # 5
    ("yellow",  "yellow_hover"),  # 6
    ("blue",    "blue_hover"),    # 7  (repeat)
]


def get_proc_btn_index(proc_name: str, fallback_index: int | None = None) -> int:
    """Return the palette slot index (0–7) for *proc_name*.

    Known procedures use their fixed slot; others fall back to
    *fallback_index* % 8, or hash(proc_name) % 8.
    """
    if proc_name in _PROC_FIXED_INDEX:
        return _PROC_FIXED_INDEX[proc_name]
    if fallback_index is not None:
        return fallback_index % 8
    return hash(proc_name) % 8


def build_stylesheet(palette: dict) -> str:
    """Build a full application QSS string from a 16-token palette dict.

    This is the single source of truth for all widget styling.  Apply it
    once on *QApplication* so every widget is covered without per-widget
    ``setStyleSheet`` calls.

    Args:
        palette: A dict with keys matching ``DARK_PALETTE`` / ``LIGHT_PALETTE``
                 (bg, fg, blue, green, …, border, selection, *_hover, …).

    Returns:
        QSS string ready to pass to ``QApplication.setStyleSheet()``.
    """
    p = palette  # shorter alias

    # Build proc-button rules for slots 0–7
    proc_btn_rules = ""
    for slot, (ck, hk) in enumerate(_SLOT_COLORS):
        proc_btn_rules += f"""
QPushButton#proc-btn-{slot} {{
    font-size: 16px;
    font-weight: 600;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    background-color: {p[ck]};
    padding: 10px;
}}
QPushButton#proc-btn-{slot}:hover {{
    background-color: {p[hk]};
    font-size: 17px;
}}
QPushButton#proc-btn-{slot}:pressed {{
    background-color: {p[hk]};
    padding-top: 12px;
    padding-bottom: 8px;
}}
"""

    # Build proc-card rules for slots 0–7
    proc_card_rules = ""
    for slot, (ck, hk) in enumerate(_SLOT_COLORS):
        proc_card_rules += f"""
QFrame#proc-card-{slot} {{
    background-color: {p['bg_sidebar']};
    border: 1px solid {p['border']};
    border-radius: 8px;
}}
QFrame#proc-card-{slot}:hover {{
    background-color: {p['bg_highlight']};
    border: 2px solid {p[hk]};
}}
"""

    return f"""
/* ── Base ─────────────────────────────────────────────────────────── */
QMainWindow, QWidget {{
    background-color: {p['bg']};
    color: {p['fg']};
}}

/* ── Labels ──────────────────────────────────────────────────────── */
QLabel {{
    color: {p['fg']};
    background-color: transparent;
}}

QLabel#page-title {{
    font-size: 22px;
    font-weight: 700;
    color: {p['fg']};
    padding-bottom: 4px;
}}

QLabel#page-subtitle {{
    font-size: 14px;
    color: {p['comment']};
    padding-bottom: 16px;
}}

QLabel#section-header {{
    font-size: 15px;
    font-weight: bold;
    color: {p['blue']};
}}

QLabel#breadcrumb {{
    font-size: 12px;
    color: {p['comment']};
}}

QLabel#success-label {{ color: {p['green']}; }}
QLabel#error-label   {{ color: {p['red']}; }}
QLabel#warning-label {{ color: {p['orange']}; }}
QLabel#info-label    {{ color: {p['blue']}; }}

/* ── Buttons (default) ────────────────────────────────────────────── */
QPushButton {{
    background-color: {p['bg_highlight']};
    color: {p['fg']};
    padding: 6px 14px;
    border: 1px solid {p['border']};
    border-radius: 4px;
}}
QPushButton:hover {{
    background-color: {p['selection']};
    border-color: {p['blue']};
}}
QPushButton:pressed {{
    background-color: {p['bg_dark']};
}}
QPushButton:disabled {{
    color: {p['comment']};
    background-color: {p['bg_dark']};
    border-color: {p['fg_gutter']};
}}

/* ── Named button variants ───────────────────────────────────────── */
QPushButton#primary-btn {{
    background-color: {p['blue']};
    color: #FFFFFF;
    font-weight: bold;
    border: none;
}}
QPushButton#primary-btn:hover  {{ background-color: {p['blue_hover']}; }}
QPushButton#primary-btn:pressed {{ background-color: {p['blue_hover']}; }}

QPushButton#danger-btn {{
    background-color: transparent;
    color: {p['red']};
    border: 1px solid {p['red']};
}}
QPushButton#danger-btn:hover {{
    background-color: {p['red']};
    color: #FFFFFF;
}}
QPushButton#danger-btn:pressed {{ background-color: {p['red_hover']}; color: #FFFFFF; }}

QPushButton#sidebar-btn {{
    background-color: transparent;
    color: {p['fg_dark']};
    border: none;
    text-align: left;
    padding: 6px 12px;
    border-radius: 4px;
}}
QPushButton#sidebar-btn:hover  {{ background-color: {p['bg_highlight']}; }}
QPushButton#sidebar-btn-quit   {{ color: {p['red']}; }}
QPushButton#sidebar-btn-quit:hover {{ background-color: {p['bg_highlight']}; color: {p['red_hover']}; }}

/* ── Procedure buttons (slots 0–7) ───────────────────────────────── */
{proc_btn_rules}

/* ── Procedure cards (slots 0–7) ────────────────────────────────── */
{proc_card_rules}

/* ── Inputs ──────────────────────────────────────────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {p['bg_highlight']};
    color: {p['fg']};
    border: 1px solid {p['border']};
    border-radius: 3px;
    padding: 4px 8px;
    selection-background-color: {p['selection']};
    selection-color: {p['fg']};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 2px solid {p['blue']};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    color: {p['comment']};
    background-color: {p['bg_dark']};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {p['bg_sidebar']};
    color: {p['fg']};
    selection-background-color: {p['selection']};
    border: 1px solid {p['border']};
}}

QPlainTextEdit {{
    background-color: {p['bg_dark']};
    color: {p['fg']};
    border: 1px solid {p['border']};
    border-radius: 3px;
    font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
    font-size: 13px;
    selection-background-color: {p['selection']};
}}

/* ── Checkboxes / radio buttons ───────────────────────────────────── */
QCheckBox, QRadioButton {{
    color: {p['fg']};
    spacing: 6px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {p['border']};
    border-radius: 3px;
    background-color: {p['bg_highlight']};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {p['blue']};
    border-color: {p['blue']};
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {p['blue']};
}}

/* ── Tables ──────────────────────────────────────────────────────── */
QTableView, QTableWidget {{
    background-color: {p['bg_dark']};
    color: {p['fg']};
    gridline-color: {p['border']};
    border: 1px solid {p['border']};
    selection-background-color: {p['selection']};
    selection-color: {p['fg']};
    alternate-background-color: {p['bg_sidebar']};
}}
QHeaderView::section {{
    background-color: {p['bg_sidebar']};
    color: {p['fg_dark']};
    padding: 4px 8px;
    border: none;
    border-bottom: 2px solid {p['blue']};
    font-weight: 600;
}}

/* ── Tree view ───────────────────────────────────────────────────── */
QTreeView {{
    background-color: {p['bg_dark']};
    color: {p['fg']};
    border: 1px solid {p['border']};
    selection-background-color: {p['selection']};
    selection-color: {p['fg']};
}}
QTreeView::item:hover {{
    background-color: {p['bg_highlight']};
}}

/* ── Progress bar ────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {p['bg_dark']};
    color: {p['fg']};
    border: 1px solid {p['border']};
    border-radius: 4px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {p['blue']};
    border-radius: 3px;
}}

/* ── Scrollbars ──────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: {p['bg_dark']};
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background-color: {p['fg_gutter']};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover  {{ background-color: {p['comment']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QScrollBar:horizontal {{
    background-color: {p['bg_dark']};
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background-color: {p['fg_gutter']};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background-color: {p['comment']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Scroll area ─────────────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

/* ── Splitter ────────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {p['border']};
}}

/* ── Menu bar & menus ────────────────────────────────────────────── */
QMenuBar {{
    background-color: {p['bg_dark']};
    color: {p['fg']};
    border-bottom: 1px solid {p['border']};
}}
QMenuBar::item:selected {{
    background-color: {p['selection']};
    color: {p['fg']};
}}
QMenu {{
    background-color: {p['bg_sidebar']};
    color: {p['fg']};
    border: 1px solid {p['border']};
}}
QMenu::item {{
    padding: 4px 24px 4px 16px;
}}
QMenu::item:selected {{
    background-color: {p['selection']};
    color: {p['fg']};
}}
QMenu::separator {{
    height: 1px;
    background-color: {p['border']};
    margin: 4px 8px;
}}

/* ── Status bar ──────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {p['bg_dark']};
    color: {p['fg_dark']};
    border-top: 1px solid {p['border']};
}}

/* ── Tool bar ────────────────────────────────────────────────────── */
QToolBar {{
    background-color: {p['bg_sidebar']};
    border: none;
    spacing: 4px;
}}

/* ── Group box ───────────────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {p['border']};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
    color: {p['fg_dark']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    color: {p['blue']};
    font-weight: 600;
}}

/* ── Separators ──────────────────────────────────────────────────── */
QFrame#separator {{
    background-color: {p['border']};
    max-height: 1px;
    border: none;
}}

/* ── Tab bar ─────────────────────────────────────────────────────── */
QTabBar::tab {{
    background-color: {p['bg_dark']};
    color: {p['fg_dark']};
    padding: 6px 16px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {p['blue']};
    border-bottom: 2px solid {p['blue']};
}}
QTabBar::tab:hover {{
    background-color: {p['bg_highlight']};
}}
QTabWidget::pane {{
    border: 1px solid {p['border']};
}}

/* ── Tooltip ─────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {p['bg_sidebar']};
    color: {p['fg']};
    border: 1px solid {p['border']};
    padding: 4px 8px;
}}
"""


def get_procedure_button_style(proc_name: str, index: int | None = None) -> str:
    """Get button style for a procedure by name.

    Known procedures (IVg, It, IV, LaserCalibration) always receive their
    fixed palette color.  Any other procedure receives a color derived from
    its grid *index* so that every button in the main grid is visually
    distinct.

    Args:
        proc_name: Procedure class name.
        index: Zero-based position in the button grid.  Used to pick a
               palette entry for procedures not in the fixed map.

    Returns:
        QSS style string for the procedure button.
    """
    c = manager().colors
    is_dark = c.is_dark

    if proc_name in _PROC_FIXED_INDEX:
        idx = _PROC_FIXED_INDEX[proc_name]
    elif index is not None:
        idx = index % len(_PROC_PALETTE)
    else:
        idx = hash(proc_name) % len(_PROC_PALETTE)

    light_bg, light_hover, dark_bg, dark_hover = _PROC_PALETTE[idx]
    bg = dark_bg if is_dark else light_bg
    hover = dark_hover if is_dark else light_hover
    return _proc_button_template(bg, hover)
