from __future__ import print_function
import sys

from PythonEditor.ui.Qt import QtGui, QtWidgets, QtCore


class PySingleton(object):
    def __new__(cls, *args, **kwargs):
        if '_the_instance' not in cls.__dict__:
            cls._the_instance = object.__new__(cls)
        return cls._the_instance


class Speaker(QtCore.QObject):
    """
    Used to relay sys stdout, stderr
    """
    emitter = QtCore.Signal(str)


class SERedirector(object):
    def __init__(self, stream, sig=None):
        fileMethods = ('fileno',
                       'flush',
                       'isatty',
                       'read',
                       'readline',
                       'readlines',
                       'seek',
                       'tell',
                       'write',
                       'writelines',
                       'xreadlines',
                       '__iter__')

        for i in fileMethods:
            if not hasattr(self, i) and hasattr(stream, i):
                setattr(self, i, getattr(stream, i))

        self.savedStream = stream
        self.sig = sig

    def write(self, text):
        if self.sig is not None:
            self.sig.emitter.emit(text)
        # sys.__stdout__.write(text)
        self.savedStream.write(text)  # TODO: should write
                                      # if not visible, else
                                      # should emit. not both!
                                      # set a global variable on
                                      # terminal visible/invisible.
    def close(self):
        self.flush()

    def stream(self):
        return self.savedStream

    def __del__(self):
        self.reset()


class SESysStdOut(SERedirector, PySingleton):
    def reset(self):
        sys.stdout = self.savedStream
        print('reset stream out')


class SESysStdErr(SERedirector, PySingleton):
    def reset(self):
        sys.stderr = self.savedStream
        print('reset stream err')
    # def write(self, text):  # TODO: Write html links here
                              # (or do it in a post process)


class Terminal(QtWidgets.QPlainTextEdit):
    """ Output text display widget """
    link_activated = QtCore.Signal(str)

    def __init__(self):
        super(Terminal, self).__init__()
        self.setStyleSheet('background:rgb(45,42,46);')

        self.setObjectName('Terminal')
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setReadOnly(True)
        self.setup()
        self.destroyed.connect(self.stop)

    @QtCore.Slot(str)
    def receive(self, text):
        try:
            textCursor = self.textCursor()
            if bool(textCursor):
                self.moveCursor(QtGui.QTextCursor.End)
                # pos = textCursor.position()
                # self.moveCursor(pos-1)
        except Exception:
            pass
        self.insertPlainText(text)
        # self.appendHtml(text)

    def stop(self):
        sys.stdout.reset()
        sys.stderr.reset()

    def setup(self):
        """
        Checks for an existing stream wrapper
        for sys.stdout and connects to it. If
        not present, creates a new one.
        TODO:
        The FnRedirect sys.stdout is always active.
        With a singleton object on a thread,
        that reads off this stream, we can make it
        available to Python Editor even before opening
        the panel.
        """

        if hasattr(sys.stdout, 'sig'):
            speaker = sys.stdout.sig
        else:
            speaker = Speaker()
            sys.stdout = SESysStdOut(sys.stdout, speaker)
            sys.stderr = SESysStdErr(sys.stderr, speaker)

        speaker.emitter.connect(self.receive)

    def mousePressEvent(self, e):
        if (e.button() == QtCore.Qt.LeftButton):
            clickedAnchor = self.anchorAt(e.pos())
            if clickedAnchor:
                self.link_activated.emit(clickedAnchor)
        super(Terminal, self).mousePressEvent(e)
