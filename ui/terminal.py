import re
import os
import sys
import shlex
from pathlib import Path

from PySide6.QtCore import QProcess, Signal, Qt
from PySide6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.inline_output import InlineInputOutput
from ui.panel_icons import panel_icon, ICON_SIZE


class TerminalPanel(QWidget):
    """A command runner whose editable command line lives in the terminal."""

    minimize_requested = Signal()
    maximize_requested = Signal()

    def __init__(self):
        super().__init__()

        self._working_dir = str(Path.home())
        self._working_directory = str(Path.cwd())

        self._output = InlineInputOutput()
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        self._output.setFont(font)
        # route submitted input to a handler that either writes to a
        # running process stdin or starts a new command
        self._output.input_submitted.connect(self._on_input_submitted)
        self._output.history_requested.connect(self.history_move)
        self._output.interrupt_requested.connect(self.stop)

        title_bar = QWidget()
        title_bar.setFixedHeight(32)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(4, 0, 4, 0)
        title_bar_layout.setSpacing(0)
        title_bar_layout.addWidget(QLabel("Terminal"))
        title_bar_layout.addStretch()

        # terminal doesn't show a separate stop control (not useful here)
        minimize_button = QPushButton()
        maximize_button = QPushButton()
        minimize_button.setToolTip("Minimize terminal")
        maximize_button.setToolTip("Maximize or restore terminal")
        minimize_button.setFixedSize(32, 24)
        minimize_button.setIcon(panel_icon("minimize"))
        minimize_button.setIconSize(ICON_SIZE)
        minimize_button.setCursor(Qt.PointingHandCursor)
        maximize_button.setFixedSize(32, 24)
        maximize_button.setIcon(panel_icon("maximize"))
        maximize_button.setIconSize(ICON_SIZE)
        maximize_button.setCursor(Qt.PointingHandCursor)
        minimize_button.clicked.connect(self.minimize_requested)
        maximize_button.clicked.connect(self.maximize_requested)
        title_bar_layout.addWidget(minimize_button)
        title_bar_layout.addWidget(maximize_button)
        # remove button borders for a cleaner title bar
        button_style = (
            "QPushButton { border: none; padding: 0px; margin: 0px; "
            "font-family: DejaVu Sans, Segoe UI, sans-serif; font-size: 12px; "
            "font-weight: normal; }"
        )
        minimize_button.setStyleSheet(button_style)
        minimize_button.setCursor(Qt.PointingHandCursor)
        minimize_button.setContentsMargins(0, 0, 0, 0)
        maximize_button.setStyleSheet(button_style)
        maximize_button.setCursor(Qt.PointingHandCursor)
        maximize_button.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(title_bar)
        layout.addWidget(self._output)

        self._process = None
        self._history: list[str] = []
        self._history_index = 0
        self._show_prompt()

    def set_working_directory(self, path: str) -> None:
        # Keep the prompt and QProcess working directory identical to the
        # active project, including when a relative path is supplied.
        working_dir = str(Path(path).expanduser().resolve())
        if not Path(working_dir).is_dir():
            return
        if working_dir != self._working_dir:
            if self._process is not None and self._process.state() != QProcess.NotRunning:
                self.stop()
            self._output.stop_input()
            self._output.clear()
        self._working_dir = working_dir
        self._working_directory = working_dir
        self._show_prompt()

    def _run_command(self, command: str) -> None:
        command = command.strip()
        self._output.stop_input()
        self._output.moveCursor(QTextCursor.End)
        self._ensure_line_break()
        if not command:
            self._show_prompt()
            return

        self._history.append(command)
        self._history_index = len(self._history)

        if self._process is not None and self._process.state() != QProcess.NotRunning:
            self._output.appendPlainText("(A command is already running, please wait.)")
            self._show_prompt()
            return

        if command == "lau c" or  command == "clear":
            self._output.clear()
            self._show_prompt()
            return

        if self._change_directory(command):
            self._show_prompt()
            return

        self._process = QProcess()
        self._output.set_interrupt_enabled(True)
        self._process.setWorkingDirectory(self._working_dir)
        # Merge stdout and stderr so error output shows up too.
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._handle_output)
        self._process.finished.connect(self._handle_finished)

        # Run through the user's native shell so quoting, pipes, and
        # shell-builtins behave as expected on each platform.
        shell, arguments = self._shell_command(command)
        self._process.start(shell, arguments)
        # Interactive programs such as `python` must be able to receive
        # stdin while they are running; waiting for process completion would
        # make the terminal appear frozen.
        self._output.start_input()

    def _change_directory(self, command: str) -> bool:
        """Handle cd in the panel so it persists between commands."""
        stripped = command.strip()
        if not stripped or stripped == "cd" or stripped.startswith("cd "):
            if stripped == "cd":
                target = Path.home()
            else:
                argument = stripped[3:].strip()
                try:
                    parts = shlex.split(argument, posix=(os.name != "nt"))
                except ValueError:
                    return False
                if len(parts) != 1:
                    return False
                target = Path(parts[0]).expanduser()
                if not target.is_absolute():
                    target = Path(self._working_dir) / target
            try:
                target = target.resolve()
            except OSError:
                return False
            if not target.is_dir():
                self._output.appendPlainText(f"cd: no such directory: {target}")
                return True
            self._working_dir = str(target)
            self._working_directory = str(target)
            return True
        return False

    @staticmethod
    def _shell_command(command: str) -> tuple[str, list[str]]:
        # Python disables its REPL prompt when stdin is a pipe. Explicitly
        # request interactive mode so `python` works with QProcess stdin.
        stripped = command.strip()
        if stripped in {"python", "python3", "py"}:
            command = f"{stripped} -i"
        if os.name == "nt" or sys.platform == "win32":
            return os.environ.get("COMSPEC", "cmd.exe"), ["/d", "/s", "/c", command]
        return os.environ.get("SHELL", "/bin/sh"), ["-c", command]

    def history_move(self, direction: int) -> None:
        if not self._history:
            return
        self._history_index = max(0, min(len(self._history), self._history_index + direction))
        value = self._history[self._history_index] if self._history_index < len(self._history) else ""
        self._output.replace_input(value)

    def _ensure_line_break(self) -> None:
        """Keep submitted terminal input separate from subsequent output."""
        # Add one separator only when the submitted line did not already
        # end with one. This avoids blank lines between ordinary commands.
        if not self._output.toPlainText().endswith("\n"):
            cursor = self._output.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertBlock()
            self._output.setTextCursor(cursor)

    def _on_input_submitted(self, text: str) -> None:
        """Handle input submitted by the inline prompt.

        If a process is running, send the input to its stdin. Otherwise,
        treat the input as a new shell command.
        """
        if self._process is not None and self._process.state() != QProcess.NotRunning:
            try:
                data = (text + "\n").encode("utf-8")
                self._process.write(data)
                # ensure data is flushed where possible
                try:
                    self._process.waitForBytesWritten(100)
                except Exception:
                    pass
                self._output.start_input()
            except Exception:
                # fallback: if writing fails, show it as a new command
                self._run_command(text)
        else:
            self._run_command(text)

    def stop(self) -> None:
        """Kill the current shell command, if one is still running."""
        if self._process is not None and self._process.state() != QProcess.NotRunning:
            self._process.kill()

    def focus_input(self) -> None:
        """Focus the current inline terminal prompt."""
        self._output.setFocus()
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._output.setTextCursor(cursor)

    def _handle_output(self) -> None:
        data = self._process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="replace")
        # QProcess output can arrive immediately after starting an
        # interactive program. Do not let the startup banner become part
        # of the editable stdin buffer.
        if self._output._input_start is not None and not self._output._input_text():
            self._output.suspend_input()
        self._output.moveCursor(QTextCursor.End)

        error_pattern = re.compile(
            r"(Traceback \(most recent call last\):|File \".*\"|\b(?:SyntaxError|NameError|ValueError|TypeError|IndexError|KeyError|AttributeError|IndentationError|TabError|AssertionError|RuntimeError|ModuleNotFoundError|ImportError)\b|Error:|Exception:)",
            re.IGNORECASE,
        )
        format_ = QTextCharFormat()
        format_.setForeground(QColor("#ff0000") if error_pattern.search(text) else QColor("#00ff00"))
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text, format_)
        self._output.setTextCursor(cursor)
        if self._process is not None and self._process.state() != QProcess.NotRunning:
            self._output.start_input()

    def _handle_finished(self, _exit_code: int, _exit_status) -> None:
        self._output.stop_input()
        self._output.set_interrupt_enabled(False)
        self._process = None
        self._show_prompt()

    def _show_prompt(self) -> None:
        current_path = self._working_dir

        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.End)
        if self._output.toPlainText() and not self._output.toPlainText().endswith("\n"):
            cursor.insertBlock()
        green_format = QTextCharFormat()
        green_format.setForeground(QColor("#00ff00"))

        cursor.setCharFormat(green_format)
        cursor.insertText(f"[{current_path}] $ ")
        # # cursor.insertText("$ ")

        self._output.setTextCursor(cursor)
        self._output.start_input()