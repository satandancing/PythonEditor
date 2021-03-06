from __future__ import print_function
import __main__
from functools import partial

from PythonEditor.ui.Qt import QtWidgets
from PythonEditor.ui.Qt import QtGui
from PythonEditor.ui.Qt import QtCore

from PythonEditor.ui.features import actions
from PythonEditor.utils.signals import connect
from PythonEditor.utils import eventfilters


def key_to_sequence(key):
    """
    Convert the given QtCore.Qt.Key type to a
    QKeySequence including currently held
    modifiers. The only downside to this being
    that, for keys that require shift to be held,
    the sequence Shift+Key will be returned.
    """
    QT = QtCore.Qt
    modifier_map = {
        QT.Key_Control : QT.ControlModifier,
        QT.Key_Shift   : QT.ShiftModifier,
        QT.Key_Alt     : QT.AltModifier,
        QT.Key_Meta    : QT.MetaModifier,
    }
    app = QtWidgets.QApplication
    held = app.keyboardModifiers()
    combo = 0
    for mod in modifier_map.values():
        if held & mod == mod:
            combo |= mod
    combo |= key

    combo = QtGui.QKeySequence(combo)
    return combo


class ShortcutHandler(QtCore.QObject):
    """
    Shortcut Manager with custom signals.

    :param editor: required `QPlainTextEdit` or `Editor` class.
    :param tabeditor: optional `QWidget` or `TabEditor`
    :param terminal: optional `QPlainTextEdit` or `Terminal` class.
    """
    def __init__(
            self,
            editor=None,
            tabeditor=None,
            terminal=None,
        ):
        super(ShortcutHandler, self).__init__()
        self.setObjectName('ShortcutHandler')
        self._installed = False

        if editor is None:
            raise Exception("""
            A text editor is necessary
            for this class.
            """.strip()
            )
        self.editor = editor

        if tabeditor is not None:
            self.tabeditor = tabeditor
            self.tabs = tabeditor.tabs
            parent_widget = tabeditor
        else:
            parent_widget = editor

        if terminal is not None:
            self.terminal = terminal
        self.parent_widget = parent_widget
        self.setParent(parent_widget)

        self.shortcut_dict = {}

        self.register_shortcuts()
        self.connect_signals()

    def connect_signals(self):
        """
        Connects the current editor's
        signals to this class
        """
        self.editor.focus_in_signal.connect(
            self.install_event_filter,
            QtCore.Qt.DirectConnection
        )
        self.editor.focus_out_signal.connect(
            self.remove_event_filter,
            QtCore.Qt.DirectConnection
        )

    def install_event_filter(self):
        if self._installed:
            return
        app = QtWidgets.QApplication.instance()
        QtCore.QCoreApplication.installEventFilter(app, self)
        self._installed = True

    def remove_event_filter(self):
        app = QtWidgets.QApplication.instance()
        QtCore.QCoreApplication.removeEventFilter(app, self)
        self._installed = False

    def eventFilter(self, obj, event):
        try:
            if not self.editor.isVisible():
                self.remove_event_filter()
                return False
        except RuntimeError:
            self.remove_event_filter()
            return False

        if not self.editor.hasFocus():
            self.remove_event_filter()
            return False

        if QtCore is None:
            return False

        if event.type() == QtCore.QEvent.Shortcut:
            if isinstance(obj, QtWidgets.QAction):
                combo = obj.shortcut()
                shortcut = combo.toString()
                action = self.shortcut_dict.get(
                    shortcut
                )
                if action is None:
                    return False
                action.trigger()
                return True

        if event.type() == QtCore.QEvent.KeyPress:
            # only let the editor receive keypress overrides
            if obj == self.editor:
                return self.handle_keypress(event)

        return False

    QtCore.Slot(QtGui.QKeyEvent)
    def handle_keypress(self, event):

        app = QtWidgets.QApplication
        held = app.keyboardModifiers()

        if (
            event.isAutoRepeat()
            and held == QtCore.Qt.NoModifier
            ):
            return False

        key = event.key()
        if key in [
            QtCore.Qt.Key_Control,
            QtCore.Qt.Key_Shift,
            QtCore.Qt.Key_Alt,
            QtCore.Qt.Key_AltGr,
            QtCore.Qt.Key_Meta,
        ]:
            return False

        # is it a Tab after a dot?
        if key == QtCore.Qt.Key_Tab:
            cursor = self.editor.textCursor()
            cursor.select(cursor.LineUnderCursor)
            text = cursor.selectedText()
            if text.endswith('.'):
                # allow autocompletion to handle this
                return False

        # try with event.text() for things
        # like " and { which appear as
        # shift+2 and shift+[ respectively
        action = self.shortcut_dict.get(
            event.text()
        )

        single_key = (action is not None)
        if not single_key:
            combo = key_to_sequence(key)
            shortcut = combo.toString()
            action = self.shortcut_dict.get(
                shortcut
            )

        if action is None:
            return False

        # need some way for the key to be
        # recognised, for example in wrap_text
        e = self.editor
        e.last_key_pressed = event.text()
        action.trigger()
        e.shortcut_overrode_keyevent = True
        if single_key:
            # it's a single key. let the
            # autocomplete do its thing
            e.post_key_pressed_signal.emit(event)
        return True

    def register_shortcuts(self, action_dict=None):
        """
        Use the shortcut register to apply
        shortcuts to actions that exist
        on the widget.
        """
        if action_dict is None:
            a = actions.load_actions_from_json
            action_dict = a()

        widgacts = action_dict.items()
        for widget_name, widget_actions in widgacts:
            if not hasattr(self, widget_name):
                continue

            widget = getattr(self, widget_name)
            if widget is None:
                continue

            acts = widget_actions.items()
            for action_name, attributes in acts:
                shortcuts = attributes['Shortcuts']
                if len(shortcuts) == 0:
                    continue
                for action in widget.actions():
                    if action.text() != action_name:
                        continue
                    break
                else:
                    continue
                key_seqs = []
                for shortcut in shortcuts:
                    key_seq = QtGui.QKeySequence(
                        shortcut
                    )

                    # convert to unicode again
                    # to make sure the format
                    # stays the same
                    s = key_seq.toString()
                    self.shortcut_dict[s] = action
                    key_seqs.append(key_seq)

                action.setShortcuts(key_seqs)
                action.setShortcutContext(
                    QtCore.Qt.WidgetWithChildrenShortcut
                )
