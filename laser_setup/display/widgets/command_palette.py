"""Command palette dialog — fuzzy-search over all QActions in the main menu."""
from ..Qt import QtCore, QtWidgets


def _collect_actions(menu):
    """Recursively yield all enabled, non-separator leaf QActions from a menu."""
    for action in menu.actions():
        if action.isSeparator() or not action.isEnabled():
            continue
        if action.menu():
            yield from _collect_actions(action.menu())
        elif action.text():
            yield action


class CommandPaletteDialog(QtWidgets.QDialog):
    """Floating search dialog over all menu actions.

    Open with Ctrl+P. Type to filter; Enter or double-click triggers the action.
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.setWindowTitle('Command Palette')
        self.setMinimumWidth(420)
        self.setWindowFlags(
            QtCore.Qt.WindowType.Dialog | QtCore.Qt.WindowType.FramelessWindowHint
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._search = QtWidgets.QLineEdit(self)
        self._search.setPlaceholderText('Type to search commands...')
        self._search.setClearButtonEnabled(True)
        layout.addWidget(self._search)

        self._list = QtWidgets.QListWidget(self)
        self._list.setMinimumHeight(200)
        layout.addWidget(self._list)

        # Collect all menu actions once
        self._actions = list(_collect_actions(main_window.menuBar()))
        self._populate('')

        self._search.textChanged.connect(self._populate)
        self._list.itemActivated.connect(self._trigger)
        self._search.returnPressed.connect(self._trigger_first)

        # Select first item on arrow down from search box
        self._search.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self._search:
            from ..Qt import QtCore as _QtCore
            if event.type() == _QtCore.QEvent.Type.KeyPress:
                key = event.key()
                if key == _QtCore.Qt.Key.Key_Down:
                    self._list.setFocus()
                    if self._list.currentRow() < 0 and self._list.count() > 0:
                        self._list.setCurrentRow(0)
                    return True
                elif key == _QtCore.Qt.Key.Key_Escape:
                    self.reject()
                    return True
        return super().eventFilter(obj, event)

    def _populate(self, text: str):
        self._list.clear()
        text_lower = text.lower()
        for action in self._actions:
            label = action.text().replace('&', '')
            tip = action.statusTip()
            if text_lower in label.lower() or text_lower in tip.lower():
                item = QtWidgets.QListWidgetItem(label)
                shortcut = action.shortcut().toString()
                if shortcut:
                    item.setText(f'{label}  ({shortcut})')
                item.setData(QtCore.Qt.ItemDataRole.UserRole, action)
                self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _trigger(self, item=None):
        if item is None:
            item = self._list.currentItem()
        if item is None:
            return
        action = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.accept()
        action.trigger()

    def _trigger_first(self):
        if self._list.count() > 0:
            self._trigger(self._list.item(0))
