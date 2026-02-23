"""Procedure card widget for the main window procedure grid.

A card-style QFrame with a coloured left-border accent, procedure name,
description, and optional keyboard shortcut badge.
"""

from ..Qt import QtCore, QtGui, QtWidgets
from ..theme import manager as theme_manager
from ..theme.qss import _SLOT_COLORS


class ProcedureCardWidget(QtWidgets.QFrame):
    """Card-style widget for a procedure entry point.

    Displays procedure name, description, and optional keyboard shortcut
    with a coloured left-border accent that tracks the current theme.
    """

    clicked = QtCore.Signal()

    def __init__(self, cls: type, slot: int, shortcut: str = "", parent=None):
        super().__init__(parent)
        self._cls = cls
        self._slot = slot % len(_SLOT_COLORS)
        self._shortcut = shortcut

        self.setObjectName(f"proc-card-{self._slot}")
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.setMinimumSize(180, 80)

        self._build_ui(cls, shortcut)
        self._apply_style()
        theme_manager().theme_changed.connect(self._apply_style)

    def _build_ui(self, cls: type, shortcut: str):
        """Build the card layout."""
        outer = QtWidgets.QHBoxLayout(self)
        outer.setContentsMargins(0, 10, 10, 10)
        outer.setSpacing(10)

        # Accent bar — left colour strip
        self._accent_bar = QtWidgets.QFrame(self)
        self._accent_bar.setObjectName(f"proc-accent-{self._slot}")
        self._accent_bar.setFixedWidth(4)
        outer.addWidget(self._accent_bar)

        # Content area
        content = QtWidgets.QVBoxLayout()
        content.setSpacing(4)

        # Top row: name + shortcut badge
        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(6)

        name = getattr(cls, 'name', cls.__name__)
        self._name_label = QtWidgets.QLabel(name, self)
        name_font = QtGui.QFont()
        name_font.setPointSize(13)
        name_font.setBold(True)
        self._name_label.setFont(name_font)
        top_row.addWidget(self._name_label)
        top_row.addStretch()

        if shortcut:
            self._shortcut_label = QtWidgets.QLabel(shortcut, self)
            sc_font = QtGui.QFont()
            sc_font.setPointSize(9)
            self._shortcut_label.setFont(sc_font)
            self._shortcut_label.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            top_row.addWidget(self._shortcut_label)

        content.addLayout(top_row)
        outer.addLayout(content)

    def _apply_style(self, _colors=None):
        """Update inline styles that depend on the current theme."""
        c = theme_manager().colors
        ck = _SLOT_COLORS[self._slot][0]
        accent = getattr(c, ck)

        self._accent_bar.setStyleSheet(
            f"background-color: {accent}; "
            f"border-top-left-radius: 7px; "
            f"border-bottom-left-radius: 7px;"
        )

        if hasattr(self, '_shortcut_label'):
            self._shortcut_label.setStyleSheet(
                f"color: {c.comment}; "
                f"background-color: {c.bg_highlight}; "
                f"border: 1px solid {c.border}; "
                f"border-radius: 3px; "
                f"padding: 1px 4px;"
            )

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Emit clicked on left button press."""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
