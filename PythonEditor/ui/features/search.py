import re

from PythonEditor.ui.Qt import QtWidgets
from PythonEditor.ui.Qt import QtGui
from PythonEditor.ui.Qt import QtCore

from PythonEditor.utils import constants


PREVIOUS_QUERY = None
PREVIOUS_REPLACEMENT = None


def remove_from_layout(layout, objectName=None):
    """
    Remove widgets with objectName
    "name" from the layout.
    """
    if objectName is None:
        return

    for i in reversed(range(layout.count())):
        item = layout.itemAt(i)
        if item is None:
            continue
        widget = item.widget()
        if widget.objectName() != objectName:
            continue
        layout.removeItem(item)
        widget.deleteLater()


class EditLine(QtWidgets.QLineEdit):
    escape_signal = QtCore.Signal()
    enter_signal = QtCore.Signal()
    def __init__(self, editor):
        super(EditLine, self).__init__(editor)
        self.editor = editor
        self.setFont(constants.DEFAULT_FONT)

    def keyPressEvent(self, event):
        esc = QtCore.Qt.Key.Key_Escape
        if event.key() == esc:
            self.editor.setFocus(QtCore.Qt.MouseFocusReason)
            self.escape_signal.emit()
            return
        enter_keys = [
            QtCore.Qt.Key.Key_Return,
            QtCore.Qt.Key.Key_Enter
        ]
        if event.key() in enter_keys:
            self.enter_signal.emit()
        super(EditLine, self).keyPressEvent(event)


class FindPalette(EditLine):
    def __init__(self, editor, tabs=None):
        super(FindPalette, self).__init__(editor)
        self.setObjectName('FindPalette')
        words = list(set(re.findall(r'\w+', editor.toPlainText())))
        completer = QtWidgets.QCompleter(words)
        completer.highlighted.connect(self.find)
        self.setCompleter(completer)
        self.editor = editor
        self.tabs = tabs
        self.search_across_tabs = True
        self.find_flags = QtGui.QTextDocument.FindCaseSensitively

        textCursor = editor.textCursor()
        global PREVIOUS_QUERY
        if textCursor.hasSelection():
            text = textCursor.selectedText()
            self.setText(text)
            PREVIOUS_QUERY = text
        elif PREVIOUS_QUERY is not None:
            self.setText(PREVIOUS_QUERY)
        else:
            self.setText('Type here to search...')
        self.setFocus(QtCore.Qt.MouseFocusReason)
        self.selectAll()

    def toggle_search_across_tabs(self):
        self.search_across_tabs = not self.search_across_tabs
        print(self.search_across_tabs)

    def focusInEvent(self, event):
        super(FindPalette, self).focusInEvent(event)

    def keyPressEvent(self, event):
        esc = QtCore.Qt.Key.Key_Escape
        if event.key() == esc:
            super(
                FindPalette, self
            ).keyPressEvent(event)
            return
        enter_keys = [
            QtCore.Qt.Key.Key_Return,
            QtCore.Qt.Key.Key_Enter
        ]
        if event.key() not in enter_keys:
            super(
                FindPalette, self
            ).keyPressEvent(event)
        elif event.modifiers() == QtCore.Qt.ControlModifier:
            self.hide()
            return
        elif self.completer().popup().isVisible():
            event.ignore()
            return

        modifier_keys = [
            QtCore.Qt.Key.Key_Shift,
            QtCore.Qt.Key.Key_Alt,
            QtCore.Qt.Key.Key_Control,
            QtCore.Qt.Key.Key_Meta,
        ]
        if event.key() in modifier_keys:
            return

        self.find()

    def lookup(self, text, text_cursor):
        """
        Reusable search.
        """
        document = self.editor.document()

        # avoid jumps by placing cursor at:
        start_pos = text_cursor.StartOfWord

        if (text_cursor.hasSelection()
            and text_cursor.selection(
            ).toPlainText() == text):

            # move on if word already matched
            start_pos = text_cursor.EndOfWord

        text_cursor.movePosition(start_pos)
        cursor = document.find(
            text,
            text_cursor,
            self.find_flags
        )
        pos = cursor.position()
        if pos != -1:
            self.editor.setTextCursor(cursor)
            return True

    backwards = False
    def find_previous(self):
        print('find previous')
        T = QtGui.QTextDocument
        self.backwards = True
        self.find_flags = T.FindCaseSensitively | T.FindBackward
        self.find()
        self.find_flags = T.FindCaseSensitively
        self.backwards = False

    def find(self):
        """
        Select text in the parent editor.
        """
        text = self.text()
        global PREVIOUS_QUERY
        PREVIOUS_QUERY = text
        editor = self.editor
        cursor = editor.textCursor()
        pos = cursor.position()

        text_cursor = self.editor.textCursor()

        # refresh highlighting
        # (this will be called later)
        self.editor.selectionChanged.emit()

        # start the search from the current position
        if self.lookup(text, text_cursor):
            return

        if self.search_across_tabs:
            count = self.tabs.count()
            current_index = self.tabs.currentIndex()
            indices = range(count)
            if not self.backwards:
                indices = indices[current_index+1:]+indices[:current_index]
            else:
                indices = reversed(indices)
                indices = indices[:current_index]+indices[current_index+1:]
                print(indices)
            for index in indices:
                data = self.tabs.tabData(index)
                body = data['text']
                if text in body:
                    self.tabs.setCurrentIndex(index)
                    break

        # search from the beginning of the document
        text_cursor = self.editor.textCursor()
        text_cursor.setPosition(
            0,
            QtGui.QTextCursor.MoveAnchor
        )
        self.lookup(text, text_cursor)
        self.editor.selectionChanged.emit()


class FindContainer(QtWidgets.QWidget):
    """
    """
    def __init__(self, editor, tabs=None, replace=False):
        super(FindContainer, self).__init__()
        self.setObjectName('FindContainer')
        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)

        self.layout().setContentsMargins(10,10,10,10)
        self.editor = editor

        self.find = FindPalette(editor, tabs=tabs)
        layout.addWidget(self.find,0,0)

        self.find_button = QtWidgets.QPushButton('Find')
        layout.addWidget(self.find_button,0,1)
        self.previous_button = QtWidgets.QPushButton('Previous')
        # layout.addWidget(self.previous_button,0,2)

        self.tabs = tabs
        if tabs is not None:
            self.search_across_tabs_check = QtWidgets.QToolButton(
                checkable=True,
                checked=True
            )
            self.search_across_tabs_check.setToolTip(
                'Search across all open tabs'
            )
            layout.addWidget(self.search_across_tabs_check,1,2)
            self.search_across_tabs_check.clicked.connect(
                self.find.toggle_search_across_tabs
            )

        if replace:
            self.replace = EditLine(editor)
            layout.addWidget(self.replace,1,0)
            self.replace_button = QtWidgets.QPushButton('Replace')
            layout.addWidget(self.replace_button,1,1)

            self.replace_button.clicked.connect(self.find_and_replace)
            self.replace.enter_signal.connect(self.find_and_replace)
            self.replace.escape_signal.connect(self.remove_from_tabeditor)

            if PREVIOUS_REPLACEMENT is not None:
                self.replace.setText(PREVIOUS_REPLACEMENT)

            self.replace.textChanged.connect(self.remember_replacement)
            self.setTabOrder(self.find, self.replace)
            # self.setTabOrder(self.replace, self.find)

        self.insert_self_in_parent()

        self.find.escape_signal.connect(self.remove_from_tabeditor)
        self.find_button.clicked.connect(self.find.find)
        self.previous_button.clicked.connect(self.find.find_previous)

    def remember_replacement(self):
        global PREVIOUS_REPLACEMENT
        PREVIOUS_REPLACEMENT = self.replace.text()

    def insert_self_in_parent(self):
        """
        encapsulate the editor in a parent widget
        for the duration of this widgets' visibility.
        """
        # remove any existing search panels first
        self.remove_from_tabeditor()

        parent = self.editor.parent()
        if parent is not None:
            self.parent_layout = parent.layout()
            index = self.parent_layout.indexOf(self.editor)
            self.parent_layout.insertWidget(index+1, self)

    def showEvent(self, event):
        super(FindContainer, self).showEvent(event)

    def remove_from_tabeditor(self):
        parent = self.editor.parent()
        if parent is None:
            return
        layout = parent.layout()
        remove_from_layout(layout, self.objectName())

    def find_and_replace(self):
        pattern = self.find.text()
        if not pattern:
            return
        replacement = self.replace.text()
        body = self.editor.toPlainText()
        count = len(re.findall(pattern, body))
        if count is 0:
            return

        ## This is probably better if replacing over multiple tabs.
        # result = QtWidgets.QMessageBox.question(
        #     self,
        #     'Find and Replace',
        #     'Replace {0} instances of "{1}" with "{2}"?'.format(count, pattern, replacement),
        #     QtWidgets.QMessageBox.Yes,
        #     QtWidgets.QMessageBox.Cancel
        # )
        # if result != QtWidgets.QMessageBox.Yes:
        #     print('User cancelled')
        #     return

        cursor = self.editor.textCursor()
        pos = cursor.position()
        cursor.movePosition(QtGui.QTextCursor.Start)
        self.editor.setTextCursor(cursor)
        while self.editor.find(pattern):
            self.editor.textCursor().insertText(replacement)

        # doc_length = ? # TODO
        # pos = max(0, min(pos, doc_length))
        cursor.setPosition(pos)
        if self.tabs is not None:
            index = self.tabs.currentIndex()
            data = self.tabs.tabData(index)
            data['text'] = self.editor.toPlainText()
            self.tabs.tab_renamed_signal.emit(
                data['uuid'],
                data['name'],
                data['text'],
                str(index),
                data.get('path')
            )
        else:
            self.editor.text_changed_signal.emit() # this is too slow

        def setFocus():
            self.editor.setFocus(QtCore.Qt.MouseFocusReason)
        QtCore.QTimer.singleShot(500, setFocus)