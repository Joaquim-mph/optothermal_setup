"""Theme color definitions with 16-token paradigm.

Single source of truth: ThemeColors carries all tokens and can produce
the palette dict expected by build_stylesheet() via as_palette_dict().
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeColors:
    """16-token color palette for a theme.

    Names follow the QT_DARK_STYLE_GUIDE convention so that ThemeColors
    and the QSS palette dict always stay in sync.
    """

    name: str               # 'dark' | 'light'
    # ── 4 background levels ──────────────────────────────────────────
    bg: str                 # main canvas
    bg_dark: str            # recessed: tables, inputs
    bg_highlight: str       # raised: buttons, hover
    bg_sidebar: str         # panel / card area
    # ── 4 text levels ────────────────────────────────────────────────
    fg: str                 # primary text
    fg_dark: str            # secondary text
    comment: str            # muted / disabled
    fg_gutter: str          # barely visible
    # ── 7 semantic accent colours ────────────────────────────────────
    blue: str               # primary accent
    cyan: str               # secondary accent
    green: str              # success
    magenta: str            # tertiary accent
    orange: str             # warning
    red: str                # danger / error
    yellow: str             # alert
    # ── 2 structural tokens ──────────────────────────────────────────
    border: str             # all dividers
    selection: str          # selected row bg
    # ── 7 hover variants ─────────────────────────────────────────────
    blue_hover: str
    cyan_hover: str
    green_hover: str
    magenta_hover: str
    orange_hover: str
    red_hover: str
    yellow_hover: str
    # ── 8 procedure colours ──────────────────────────────────────────
    proc_ivg: str
    proc_ivg_hover: str
    proc_it: str
    proc_it_hover: str
    proc_iv: str
    proc_iv_hover: str
    proc_laser: str
    proc_laser_hover: str

    def as_palette_dict(self) -> dict:
        """Return the 16+7 token dict expected by build_stylesheet()."""
        return {
            'bg': self.bg, 'bg_dark': self.bg_dark,
            'bg_highlight': self.bg_highlight, 'bg_sidebar': self.bg_sidebar,
            'fg': self.fg, 'fg_dark': self.fg_dark,
            'comment': self.comment, 'fg_gutter': self.fg_gutter,
            'blue': self.blue, 'cyan': self.cyan, 'green': self.green,
            'magenta': self.magenta, 'orange': self.orange,
            'red': self.red, 'yellow': self.yellow,
            'border': self.border, 'selection': self.selection,
            'blue_hover': self.blue_hover, 'cyan_hover': self.cyan_hover,
            'green_hover': self.green_hover, 'magenta_hover': self.magenta_hover,
            'orange_hover': self.orange_hover, 'red_hover': self.red_hover,
            'yellow_hover': self.yellow_hover,
        }


def create_dark_theme() -> ThemeColors:
    """Create dark theme using Tokyo Night palette."""
    return ThemeColors(
        name="dark",
        bg="#1a1b26", bg_dark="#16161e", bg_highlight="#292e42", bg_sidebar="#1f2335",
        fg="#c0caf5", fg_dark="#a9b1d6", comment="#565f89", fg_gutter="#3b4261",
        blue="#7aa2f7", cyan="#7dcfff", green="#9ece6a", magenta="#bb9af7",
        orange="#ff9e64", red="#f7768e", yellow="#e0af68",
        border="#3b4261", selection="#283457",
        blue_hover="#a9c1ff", cyan_hover="#a5e5ff", green_hover="#b9e08a",
        magenta_hover="#d0b4ff", orange_hover="#ffb885", red_hover="#ff9aab",
        yellow_hover="#f0c88a",
        proc_ivg="#4A90E2", proc_ivg_hover="#60A5FA",
        proc_it="#22C55E",  proc_it_hover="#4ADE80",
        proc_iv="#EF4444",  proc_iv_hover="#F87171",
        proc_laser="#F59E0B", proc_laser_hover="#FBBF24",
    )


def create_light_theme() -> ThemeColors:
    """Create light theme."""
    return ThemeColors(
        name="light",
        bg="#F8F9FA", bg_dark="#F0F2F4", bg_highlight="#E9ECEF", bg_sidebar="#F1F3F5",
        fg="#1A1A1A", fg_dark="#495057", comment="#868E96", fg_gutter="#CED4DA",
        blue="#2563EB", cyan="#0891B2", green="#16A34A", magenta="#7C3AED",
        orange="#D97706", red="#DC2626", yellow="#B45309",
        border="#D1D5DB", selection="#DBEAFE",
        blue_hover="#1D4ED8", cyan_hover="#0E7490", green_hover="#15803D",
        magenta_hover="#6D28D9", orange_hover="#B45309", red_hover="#B91C1C",
        yellow_hover="#92400E",
        proc_ivg="#2563EB", proc_ivg_hover="#1D4ED8",
        proc_it="#16A34A",  proc_it_hover="#15803D",
        proc_iv="#DC2626",  proc_iv_hover="#B91C1C",
        proc_laser="#D97706", proc_laser_hover="#B45309",
    )
