from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

class InlineInputOutput(QPlainTextEdit):
    """Output view that accepts one answer directly after a program prompt."""

    input_submitted = Signal(str)
    interrupt_requested = Signal()
    history_requested = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._interrupt_enabled = False
        self._input_start: int | None = None
        self.setReadOnly(True)

    def start_input(self) -> None:
        """Make the text after the current output the editable answer area."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        self._input_start = cursor.position()
        self.setReadOnly(False)
        self.setFocus(Qt.OtherFocusReason)

    def stop_input(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        # conditional para if user input ang code ay magkakaroon ng \n 
        if self._input_start is not None and self._input_text():
            cursor.insertText("\n")

        self.setTextCursor(cursor)

        self._input_start = None
        self.setReadOnly(True)

    def _input_end(self) -> int:
        return self.document().characterCount() - 1

    def _move_to_input_end(self) -> None:
        cursor = self.textCursor()
        cursor.setPosition(self._input_end())
        self.setTextCursor(cursor)

    def _input_text(self) -> str:
        cursor = self.textCursor()
        cursor.setPosition(self._input_start)
        cursor.setPosition(self._input_end(), QTextCursor.KeepAnchor)
        return cursor.selectedText().replace("\u2029", "\n")

    def keyPressEvent(self, event) -> None:

        if (event.key() == Qt.Key_C
        and event.modifiers() & Qt.ControlModifier):
            
            if self.textCursor().hasSelection():
                selection = QTextCursor(self.textCursor())
                self.copy()
                self.setTextCursor(selection)
                return
            if self._interrupt_enabled:
                self.interrupt_requested.emit()
                return

        if self._input_start is None:
            super().keyPressEvent(event)
            return

        key = event.key()
        cursor = self.textCursor()
        selection_start = cursor.selectionStart()

        if key in (Qt.Key_Return, Qt.Key_Enter):
            self.input_submitted.emit(self._input_text())
            return

        if key == Qt.Key_A and event.modifiers() & Qt.ControlModifier:
            cursor.setPosition(self._input_start)
            cursor.setPosition(self._input_end(), QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)
            return

        if key in (Qt.Key_Up, Qt.Key_Down) and not (event.modifiers() & Qt.ShiftModifier):
            self.history_requested.emit(-1 if key == Qt.Key_Up else 1)
            return

        if key == Qt.Key_Backspace and cursor.position() <= self._input_start:
            return

        if key == Qt.Key_Delete and selection_start < self._input_start:
            return

        if key == Qt.Key_Left and cursor.position() <= self._input_start:
            return

        if key == Qt.Key_Home:
            cursor.setPosition(self._input_start)
            self.setTextCursor(cursor)
            return

        # if key == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
        #     self.interrupt_requested.emmit()
        #     return

        # The program's output is protected. If the user clicked in it,
        # continue editing at the active prompt instead.
        if selection_start < self._input_start:
            self._move_to_input_end()

        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._input_start is None:
            super().mousePressEvent(event)
            return

        # Keep the clicked selection intact so users can select and copy
        # any previous command output. Key presses still redirect edits
        # away from the protected output below.
        super().mousePressEvent(event)

    def set_interrupt_enabled(self, enabled: bool) -> None:
        self._interrupt_enabled = enabled

    def suspend_input(self) -> None:
        """Protect existing output without adding a newline."""
        self._input_start = None
        self.setReadOnly(True)

    def replace_input(self, text: str) -> None:
        if self._input_start is None:
            return
        cursor = self.textCursor()
        cursor.setPosition(self._input_start)
        cursor.setPosition(self._input_end(), QTextCursor.KeepAnchor)
        cursor.insertText(text)
        self.setTextCursor(cursor)
