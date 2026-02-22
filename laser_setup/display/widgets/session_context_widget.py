"""Persistent chip/sample context panel for the main window."""
import logging

from ..Qt import QtCore, QtWidgets

log = logging.getLogger(__name__)


class SessionContextWidget(QtWidgets.QGroupBox):
    """Persistent chip/sample context panel.

    Displayed above the main procedure buttons. Pre-fills matching parameters
    on each newly opened ExperimentWindow.
    """

    context_changed = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__('Session Context', parent)

        try:
            from ...config import CONFIG
            chip_choices = list(CONFIG.parameters.Chip.chip_group.choices)
            sample_choices = list(CONFIG.parameters.Chip.sample.choices)
        except Exception:
            chip_choices = ['other']
            sample_choices = ['other', 'A', 'B', 'C', 'D']

        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        self._chip_group = QtWidgets.QComboBox(self)
        self._chip_group.addItems(chip_choices)
        layout.addRow('Chip Group:', self._chip_group)

        self._chip_number = QtWidgets.QSpinBox(self)
        self._chip_number.setMinimum(1)
        self._chip_number.setValue(1)
        layout.addRow('Chip #:', self._chip_number)

        self._sample = QtWidgets.QComboBox(self)
        self._sample.addItems(sample_choices)
        layout.addRow('Sample:', self._sample)

        self._info = QtWidgets.QLineEdit(self)
        self._info.setPlaceholderText('Free text...')
        layout.addRow('Info:', self._info)

        # Emit context_changed when any field changes
        self._chip_group.currentTextChanged.connect(self._emit_changed)
        self._chip_number.valueChanged.connect(self._emit_changed)
        self._sample.currentTextChanged.connect(self._emit_changed)
        self._info.textChanged.connect(self._emit_changed)

    def get_context(self) -> dict:
        """Return the current session context as a dict."""
        return {
            'chip_group': self._chip_group.currentText(),
            'chip_number': self._chip_number.value(),
            'sample': self._sample.currentText(),
            'info': self._info.text(),
        }

    def _emit_changed(self, *_):
        self.context_changed.emit(self.get_context())
