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

    @property
    def is_dark(self) -> bool:
        """Whether this is a dark theme (all non-light themes are dark)."""
        return self.name != "light"

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


def create_dracula_theme() -> ThemeColors:
    """Create Dracula theme (https://draculatheme.com/contribute)."""
    return ThemeColors(
        name="dracula",
        bg="#282a36", bg_dark="#21222c", bg_highlight="#44475a", bg_sidebar="#21222c",
        fg="#f8f8f2", fg_dark="#c8c8c0", comment="#6272a4", fg_gutter="#44475a",
        blue="#bd93f9", cyan="#8be9fd", green="#50fa7b", magenta="#ff79c6",
        orange="#ffb86c", red="#ff5555", yellow="#f1fa8c",
        border="#44475a", selection="#44475a",
        blue_hover="#d0b5ff", cyan_hover="#a8ecff", green_hover="#7dfca0",
        magenta_hover="#ff96d4", orange_hover="#ffca8a", red_hover="#ff7575",
        yellow_hover="#f5fdad",
        proc_ivg="#bd93f9", proc_ivg_hover="#d0b5ff",
        proc_it="#50fa7b",  proc_it_hover="#7dfca0",
        proc_iv="#ff5555",  proc_iv_hover="#ff7575",
        proc_laser="#ffb86c", proc_laser_hover="#ffca8a",
    )


def create_catppuccin_theme() -> ThemeColors:
    """Create Catppuccin Mocha theme (https://github.com/catppuccin/catppuccin)."""
    return ThemeColors(
        name="catppuccin",
        bg="#1e1e2e", bg_dark="#181825", bg_highlight="#313244", bg_sidebar="#181825",
        fg="#cdd6f4", fg_dark="#bac2de", comment="#6c7086", fg_gutter="#313244",
        blue="#89b4fa", cyan="#89dceb", green="#a6e3a1", magenta="#cba6f7",
        orange="#fab387", red="#f38ba8", yellow="#f9e2af",
        border="#45475a", selection="#313244",
        blue_hover="#b4d2ff", cyan_hover="#aae6f0", green_hover="#c3edbe",
        magenta_hover="#dbc3ff", orange_hover="#fcc8a8", red_hover="#f7afc0",
        yellow_hover="#fbecc8",
        proc_ivg="#89b4fa", proc_ivg_hover="#b4d2ff",
        proc_it="#a6e3a1",  proc_it_hover="#c3edbe",
        proc_iv="#f38ba8",  proc_iv_hover="#f7afc0",
        proc_laser="#fab387", proc_laser_hover="#fcc8a8",
    )


def create_solarized_dark_theme() -> ThemeColors:
    """Create Solarized Dark theme (https://ethanschoonover.com/solarized/)."""
    return ThemeColors(
        name="solarized_dark",
        bg="#002b36", bg_dark="#00212b", bg_highlight="#073642", bg_sidebar="#073642",
        fg="#839496", fg_dark="#657b83", comment="#586e75", fg_gutter="#073642",
        blue="#268bd2", cyan="#2aa198", green="#859900", magenta="#d33682",
        orange="#cb4b16", red="#dc322f", yellow="#b58900",
        border="#073642", selection="#073642",
        blue_hover="#4aa8e8", cyan_hover="#4bbcb4", green_hover="#a3ba00",
        magenta_hover="#e054a0", orange_hover="#e06830", red_hover="#f04848",
        yellow_hover="#d4a010",
        proc_ivg="#268bd2", proc_ivg_hover="#4aa8e8",
        proc_it="#859900",  proc_it_hover="#a3ba00",
        proc_iv="#dc322f",  proc_iv_hover="#f04848",
        proc_laser="#cb4b16", proc_laser_hover="#e06830",
    )


def create_gruvbox_theme() -> ThemeColors:
    """Create Gruvbox Dark theme (https://github.com/morhetz/gruvbox)."""
    return ThemeColors(
        name="gruvbox",
        bg="#282828", bg_dark="#1d2021", bg_highlight="#3c3836", bg_sidebar="#32302f",
        fg="#ebdbb2", fg_dark="#d5c4a1", comment="#928374", fg_gutter="#504945",
        blue="#83a598", cyan="#8ec07c", green="#b8bb26", magenta="#d3869b",
        orange="#fe8019", red="#fb4934", yellow="#fabd2f",
        border="#504945", selection="#3c3836",
        blue_hover="#a3c5b8", cyan_hover="#aed89c", green_hover="#d4d640",
        magenta_hover="#e8a4b8", orange_hover="#ffa040", red_hover="#fc6a50",
        yellow_hover="#fcd060",
        proc_ivg="#83a598", proc_ivg_hover="#a3c5b8",
        proc_it="#b8bb26",  proc_it_hover="#d4d640",
        proc_iv="#fb4934",  proc_iv_hover="#fc6a50",
        proc_laser="#fe8019", proc_laser_hover="#ffa040",
    )


def create_monokai_theme() -> ThemeColors:
    """Create Monokai Dark theme (https://monokai.pro)."""
    return ThemeColors(
        name="monokai",
        bg="#272822", bg_dark="#1e1f1c", bg_highlight="#3e3d32", bg_sidebar="#2d2e27",
        fg="#f8f8f2", fg_dark="#cfcfc2", comment="#75715e", fg_gutter="#49483e",
        blue="#66d9e8", cyan="#a1efe4", green="#a6e22e", magenta="#ae81ff",
        orange="#fd971f", red="#f92672", yellow="#e6db74",
        border="#49483e", selection="#49483e",
        blue_hover="#8ae8f4", cyan_hover="#c0f5ef", green_hover="#c4f04e",
        magenta_hover="#c9a8ff", orange_hover="#ffb347", red_hover="#ff5294",
        yellow_hover="#f5ef94",
        proc_ivg="#66d9e8", proc_ivg_hover="#8ae8f4",
        proc_it="#a6e22e",  proc_it_hover="#c4f04e",
        proc_iv="#f92672",  proc_iv_hover="#ff5294",
        proc_laser="#fd971f", proc_laser_hover="#ffb347",
    )
