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
            background-color: {c.accent_primary};
            color: #FFFFFF;
            padding: 8px 20px;
            border: none;
            border-radius: 4px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {c.accent_primary_hover};
        }}
        QPushButton:pressed {{
            background-color: {c.accent_primary_hover};
            padding-top: 10px;
            padding-bottom: 6px;
        }}
        QPushButton:disabled {{
            background-color: {c.fg_disabled};
            color: {c.bg_tertiary};
        }}
    """


def _button_secondary() -> str:
    """Secondary/neutral button style."""
    c = manager().colors
    return f"""
        QPushButton {{
            background-color: {c.bg_tertiary};
            color: {c.fg_primary};
            padding: 8px 16px;
            border: 1px solid {c.border_primary};
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {c.border_primary};
            border-color: {c.border_focus};
        }}
        QPushButton:pressed {{
            background-color: {c.border_secondary};
        }}
    """


def _button_danger() -> str:
    """Danger/delete button style."""
    c = manager().colors
    return f"""
        QPushButton {{
            background-color: {c.danger};
            color: #FFFFFF;
            border: none;
            border-radius: 3px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {c.danger_hover};
        }}
        QPushButton:pressed {{
            background-color: {c.danger_hover};
        }}
    """


def _button_success() -> str:
    """Success/confirm button style."""
    c = manager().colors
    return f"""
        QPushButton {{
            background-color: {c.success};
            color: #FFFFFF;
            padding: 8px 20px;
            border: none;
            border-radius: 4px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {c.success_hover};
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
            background-color: {c.bg_secondary};
            border: 1px solid {c.border_primary};
            border-radius: 5px;
        }}
        QFrame:hover {{
            border-color: {c.accent_primary};
            border-width: 2px;
        }}
        QLabel {{
            color: {c.fg_primary};
            background-color: transparent;
            border: none;
        }}
        QToolButton {{
            color: {c.fg_primary};
            background-color: transparent;
            border: none;
        }}
    """


def _card_hover() -> str:
    """Card style with active hover state."""
    c = manager().colors
    return f"""
        QFrame {{
            background-color: {c.bg_secondary};
            border: 2px solid {c.accent_primary};
            border-radius: 5px;
        }}
        QLabel {{
            color: {c.fg_primary};
            background-color: transparent;
            border: none;
        }}
    """


def _label_primary() -> str:
    """Primary label style."""
    c = manager().colors
    return f"color: {c.fg_primary};"


def _label_secondary() -> str:
    """Secondary/subdued label style."""
    c = manager().colors
    return f"color: {c.fg_secondary};"


def _label_info() -> str:
    """Info/accent colored label style."""
    c = manager().colors
    return f"color: {c.info}; font-style: italic;"


def _input() -> str:
    """Input field style (line edit, combo box)."""
    c = manager().colors
    return f"""
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            background-color: {c.bg_tertiary};
            color: {c.fg_primary};
            border: 1px solid {c.border_primary};
            border-radius: 3px;
            padding: 4px 8px;
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {c.border_focus};
            border-width: 2px;
        }}
    """


def _scroll_area() -> str:
    """Scroll area style for sequence builder."""
    c = manager().colors
    return f"""
        QScrollArea {{
            border: 2px dashed {c.border_primary};
            border-radius: 8px;
            background-color: {c.bg_secondary};
        }}
    """


def get_procedure_button_style(proc_name: str) -> str:
    """Get button style for a procedure by name.

    Args:
        proc_name: Procedure name (IVg, It, IV, LaserCalibration)

    Returns:
        QSS style string for the procedure button
    """
    style_map = {
        'IVg': 'button_proc_ivg',
        'It': 'button_proc_it',
        'IV': 'button_proc_iv',
        'LaserCalibration': 'button_proc_laser',
    }
    style_name = style_map.get(proc_name, 'button_primary')
    return qss(style_name)
