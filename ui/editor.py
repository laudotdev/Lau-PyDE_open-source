import ast
import difflib
import tokenize
from io import StringIO
from PySide6.QtCore import QRect, QRegularExpression, QSize, Qt, Signal, QTimer, QPoint, QEvent
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextFormat,
    QTextCursor,
    QAction,
    QShortcut,
    QKeySequence,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget, QMenu, QCompleter, QApplication
from PySide6.QtCore import QStringListModel

PYTHON_KEYWORDS = [
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield",
]

PYTHON_BUILTINS = [
    "print", "len", "range", "str", "int", "float", "bool", "list",
    "dict", "set", "tuple", "open", "input", "type", "isinstance",
    "enumerate", "zip", "map", "filter", "sorted", "sum", "min", "max",
    "abs", "super", "self",
]

# Small, static attribute lists for common modules to provide attribute completions
MODULE_ATTRS = {
    "os": [
        "listdir", "path", "getcwd", "chdir", "mkdir", "makedirs", "remove", "rename",
    ],
    "sys": ["argv", "exit", "path", "stdin", "stdout", "stderr"],
    "math": ["sqrt", "sin", "cos", "tan", "pi", "e"],
    "json": ["load", "loads", "dump", "dumps"],
    "pathlib": ["Path", "PurePath"],
}


class PythonHighlighter(QSyntaxHighlighter):
    """
    Colors Python source code as the user types.

    A QSyntaxHighlighter works by checking each line of text against a
    list of (regular expression, text format) rules and applying the
    matching color. Qt calls our `highlightBlock` method automatically
    whenever a line of text changes — we never call it ourselves.
    """

    def __init__(self, document):
        super().__init__(document)
        self._rules = []

        def make_format(color: str, bold: bool = False) -> QTextCharFormat:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Bold)
            return fmt

        keyword_format = make_format("#c586c0", bold=True)
        for word in PYTHON_KEYWORDS:
            self._rules.append((QRegularExpression(rf"\b{word}\b"), keyword_format))

        builtin_format = make_format("#4ec9b0")
        for word in PYTHON_BUILTINS:
            self._rules.append((QRegularExpression(rf"\b{word}\b"), builtin_format))

        # def/class name — highlight just the captured name (group 1),
        # not the keyword itself (the keyword already gets colored above).
        function_name_format = make_format("#dcdcaa")
        self._rules.append((QRegularExpression(r"\bdef\s+(\w+)"), function_name_format))

        class_name_format = make_format("#4ec9b0", bold=True)
        self._rules.append((QRegularExpression(r"\bclass\s+(\w+)"), class_name_format))

        number_format = make_format("#b5cea8")
        self._rules.append((QRegularExpression(r"\b[0-9]+\.?[0-9]*\b"), number_format))

        string_format = make_format("#ce9178")
        f_string_variable_format = make_format("#9CDCFE")

        self._rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
        self._rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self._rules.append(
            (
                QRegularExpression(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"),
                    f_string_variable_format,
            )
        )

        self._comment_format = make_format("#6a9955")
        self._comment_pattern = QRegularExpression(r"#[^\n]*")

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                # Patterns with a capture group (def/class names) should
                # only color the captured name, not the whole match.
                if match.lastCapturedIndex() >= 1:
                    start, length = match.capturedStart(1), match.capturedLength(1)
                else:
                    start, length = match.capturedStart(), match.capturedLength()
                self.setFormat(start, length, fmt)

        # comments are applied last so "#" inside a comment always wins,
        # even if part of the comment text matched an earlier rule.
        comment_iterator = self._comment_pattern.globalMatch(text)
        while comment_iterator.hasNext():
            match = comment_iterator.next()
            self.setFormat(match.capturedStart(), match.capturedLength(), self._comment_format)


class LineNumberArea(QWidget):
    """
    A thin widget drawn to the left of the editor that shows line numbers.

    It doesn't do any work itself — it just asks its parent CodeEditor
    to paint into it. This "delegate the painting back to the editor"
    pattern is the standard Qt approach for line-number gutters.
    """

    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.paint_line_numbers(event)


def _keyword_suggestion(token_text: str) -> str | None:
    """Return a likely keyword typo suggestion only for genuinely close matches.

    This rejects valid Python identifiers such as ``model`` while still catching
    actual misspellings like ``frmo`` -> ``from`` or ``forr`` -> ``for``.
    """
    if not token_text:
        return None

    best_match = None
    best_ratio = 0.0
    for keyword in PYTHON_KEYWORDS:
        if keyword == token_text:
            continue
        if abs(len(token_text) - len(keyword)) > 1:
            continue

        ratio = difflib.SequenceMatcher(None, token_text, keyword).ratio()
        if ratio >= 0.85 and ratio > best_ratio:
            best_match = keyword
            best_ratio = ratio

    return best_match


class CodeEditor(QPlainTextEdit):
    # notify listeners when diagnostics/count changes: emits int (total issues)
    diagnostics_changed = Signal(int)
    """
    The main code-editing widget.

    Inherits from QPlainTextEdit, which already gives us text editing,
    copy/paste/cut/undo/redo, and keyboard navigation for free — we
    only add what's specific to a code editor: line numbers, syntax
    highlighting, and auto-indentation.
    """

    def __init__(self):
        super().__init__()
        # this block is for the Ctrl+Shift+H shortcut to highlight all instances of the selected word
        self.highlight_shortcut = QShortcut(
            QKeySequence("Ctrl+Shift+H"), self
        )
        self.highlight_shortcut.activated.connect(
            self.syntax_highlight_change
        )

        self.multi_cursor_positions = []
        self.multi_cursor_active = False
        self._multi_cursor_word = ""
        self._multi_cursor_replacement = ""
        self._multi_cursor_starts = []
        self._multi_cursor_original_length = 0

        # A monospace font is essential for code so columns line up.
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(11)
        self.setFont(font)

        # self._error_line = None
        # self._error_start = None
        # self._error_end = None
        self._syntax_errors = []
        self._keyword_errors = []
        self._name_errors = []
        self._parse_error_message: str | None = None

        # Code editors traditionally scroll sideways rather than wrap.
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self._line_number_mode = "absolute"

        self._line_number_area = LineNumberArea(self)

        # blockCountChanged/updateRequest/cursorPositionChanged already
        # exist on QPlainTextEdit — we connect to them ("signals and
        # slots") to keep the line-number gutter in sync as the user types.
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self._update_line_number_area_width(0)
        self._highlight_current_line()

        self._highlighter = PythonHighlighter(self.document())
        # connect textChanged after setting up completion model to avoid
        # running _check_errors before instance attributes are initialized

        # track last emitted diagnostics count to avoid noisy emissions
        self._last_diag_count = -1

        # lightweight completion: keywords, builtins, and user-defined names
        self._completion_model = QStringListModel()
        self._positioning_completion_popup = False
        self._completer = QCompleter(self._completion_model, self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.popup().installEventFilter(self)
        self._completion_model.modelReset.connect(self._reposition_completion_popup)
        self._completion_model.rowsInserted.connect(self._reposition_completion_popup)
        self._completion_model.rowsRemoved.connect(self._reposition_completion_popup)
        self.cursorPositionChanged.connect(self._reposition_completion_popup)
        self.updateRequest.connect(self._reposition_completion_popup)

        # now safe to connect textChanged
        self.textChanged.connect(self._check_errors)

    def get_error_messages(self) -> list[str]:
        """Return human-readable error messages for all current issues."""
        self._check_errors()

        messages: list[str] = []

        for index, (line, start, end) in enumerate(self._syntax_errors):
            block = self.document().findBlockByLineNumber(line - 1)
            if not block.isValid():
                messages.append(f"Line {line}: Syntax error.")
                continue
            text = block.text().strip()
            if self._parse_error_message and index == 0:
                messages.append(f"Line {line}: {self._parse_error_message}")
                continue
            if not text:
                messages.append(f"Line {line}: Syntax error.")
                continue
            messages.append(f"Line {line}: Syntax error near '{text}'.")

        for line, start, end in self._keyword_errors:
            block = self.document().findBlockByLineNumber(line - 1)

            if not block.isValid():
                messages.append(f"Line {line}: Possible keyword typo.")
                continue

            text = block.text()
            token_text = text[start:end].strip()

            if not token_text:
                messages.append(f"Line {line}: Possible keyword typo.")
                continue

            suggestion = _keyword_suggestion(token_text)

            if suggestion:
                messages.append(
                    f"Line {line}: '{token_text}' is not valid Python. "
                    f"Did you mean '{suggestion}'?"
                )
            else:
                messages.append(
                    f"Line {line}: '{token_text}' is not valid Python."
                )

        for line, start, end in self._name_errors:
            block = self.document().findBlockByLineNumber(line - 1)
            if not block.isValid():
                messages.append(f"Line {line}: name error.")
                continue
            text = block.text()
            token_text = text[start:end].strip()
            if not token_text:
                messages.append(f"Line {line}: name error.")
                continue
            messages.append(f"Line {line}: '{token_text}' is not recognized. Check the spelling or name.")

        return messages

    def _error_line_numbers(self) -> set[int]:
        """Return all line numbers that currently have a detected error."""
        error_lines: set[int] = set()
        for line, _, _ in self._syntax_errors:
            error_lines.add(line)
        for line, _, _ in self._keyword_errors:
            error_lines.add(line)
        for line, _, _ in self._name_errors:
            error_lines.add(line)
        return error_lines

    def _collect_defined_names(self, tree: ast.AST) -> set[str]:
        """Collect names that are actually defined in the code so we do not
        flag valid variables as misspellings or undefined names."""
        defined: set[str] = set()
        imports: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(node.name)
            elif isinstance(node, ast.arg):
                defined.add(node.arg)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                defined.add(node.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    defined.add(name)
                    imports.add(name)

        return defined, imports

    def _get_enclosing_scope_names(self, tree: ast.AST, cursor_line: int) -> set[str]:
        """Return names defined in the smallest enclosing function/class for cursor_line.

        Falls back to empty set when no enclosing scope found.
        """
        candidates = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = getattr(node, 'lineno', None)
                end = getattr(node, 'end_lineno', None)
                if start is None:
                    continue
                if end is None:
                    # approximate end_lineno by scanning child nodes
                    end = start
                    for sub in ast.walk(node):
                        if hasattr(sub, 'lineno'):
                            end = max(end, getattr(sub, 'lineno'))

                if start <= cursor_line <= end:
                    # collect names defined directly under this node
                    names = set()
                    for sub in ast.walk(node):
                        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            names.add(sub.name)
                        elif isinstance(sub, ast.arg):
                            names.add(sub.arg)
                        elif isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                            names.add(sub.id)
                        elif isinstance(sub, (ast.Import, ast.ImportFrom)):
                            for alias in sub.names:
                                names.add(alias.asname or alias.name.split('.')[0])
                    candidates.append((start, end, names))

        if not candidates:
            return set()

        # choose the smallest enclosing scope (shortest range)
        candidates.sort(key=lambda t: (t[1] - t[0], t[0]))
        return candidates[0][2]

    def _check_errors(self) -> None:
        code = self.toPlainText()

        # self._error_line = None
        # self._error_start = None
        # self._error_end = None
        self._syntax_errors = []
        self._keyword_errors = []
        self._name_errors = []
        self._parse_error_message = None
        seen_syntax = set()
        seen_keyword = set()
        seen_name = set()

        try:
            list(tokenize.generate_tokens(StringIO(code).readline))
        except (tokenize.TokenError, IndentationError) as error:
            message, location = error.args

            if isinstance(error, IndentationError):
                line = error.lineno or 1
                column = error.offset or 0
                item = (line, column + 1, column + 2)
            elif location:
                line, column = location[0], location[1]
                item = (line, column + 1, column + 2)
                if item not in seen_syntax:
                    self._syntax_errors.append(item)
                    seen_syntax.add(item)

        tokens = []

        try:
            tokens = list(tokenize.generate_tokens(StringIO(code).readline))
        except (tokenize.TokenError, IndentationError):
            pass

        at_statement_start = True

        for token in tokens:
            if token.type == tokenize.NEWLINE:
                at_statement_start = True
                continue

            if token.type in (tokenize.INDENT, tokenize.DEDENT):
                continue

            # Only consider names that start a statement. Ignore known
            # builtins (including `self`) so they are never suggested as
            # keyword typos.
            if at_statement_start and token.type == tokenize.NAME:
                if token.string in PYTHON_BUILTINS:
                    at_statement_start = False
                    continue

                if token.string not in PYTHON_KEYWORDS:
                    suggestion = _keyword_suggestion(token.string)
                    if suggestion:
                        item = (
                            token.start[0],
                            token.start[1],
                            token.end[1],
                        )
                        if item not in seen_keyword:
                            self._keyword_errors.append(item)
                            seen_keyword.add(item)

                at_statement_start = False

        self._name_errors = []

        defined_names: set[str] = set()

        try:
            tree = ast.parse(code)
            defined_names, imports = self._collect_defined_names(tree)
            # find enclosing scope names for the cursor (if available)
            cursor = self.textCursor()
            cursor_line = cursor.blockNumber() + 1
            scope_names = self._get_enclosing_scope_names(tree, cursor_line)
            # Build a ranked completion list:
            # 1) defined names (most frequent first), 2) builtins (used first),
            # 3) remaining builtins, 4) keywords.
            try:
                from collections import Counter

                name_counts = Counter()
                try:
                    toks = list(tokenize.generate_tokens(StringIO(code).readline))
                except Exception:
                    toks = []

                for t in toks:
                    if t.type == tokenize.NAME:
                        name_counts[t.string] += 1

                # defined names sorted by whether they're in scope, then frequency then name
                def defined_key(n):
                    in_scope = 0 if n in scope_names else 1
                    return (in_scope, -name_counts.get(n, 0), n)

                defined_sorted = sorted(defined_names, key=defined_key)

                # builtins seen in the file first (by frequency), then remaining builtins
                builtin_seen = [b for b in PYTHON_BUILTINS if name_counts.get(b, 0) > 0]
                builtin_seen.sort(key=lambda b: -name_counts.get(b, 0))
                builtin_remaining = [b for b in PYTHON_BUILTINS if b not in builtin_seen]

                # keywords: include all but keep them low-priority
                keywords_sorted = sorted(PYTHON_KEYWORDS)

                suggestion_list = []
                suggestion_list.extend(defined_sorted)
                suggestion_list.extend(builtin_seen)
                suggestion_list.extend(builtin_remaining)
                suggestion_list.extend(keywords_sorted)

                # deduplicate while preserving order
                seen = set()
                final_list = []
                for s in suggestion_list:
                    if s in seen:
                        continue
                    seen.add(s)
                    final_list.append(s)

                # keep the suggestion list compact
                MAX_SUGGESTIONS = 60
                self._completion_model.setStringList(final_list[:MAX_SUGGESTIONS])
            except Exception:
                # fall back to a simple combined list if anything goes wrong
                try:
                    completions = set(PYTHON_KEYWORDS + PYTHON_BUILTINS) | set(defined_names)
                    self._completion_model.setStringList(sorted(completions))
                except Exception:
                    pass
        except SyntaxError as error:
            if isinstance(error, IndentationError):
                detail = str(error).strip() or "unexpected indentation"
                self._parse_error_message = f"IndentationError: {detail}"
            if error.lineno is not None and error.offset is not None:
                start = error.offset
                end = getattr(error, "end_offset", None)

                self._syntax_errors.append(
                    (
                        error.lineno,
                        start,
                        end,
                    )
                )

            self._highlight_current_line()
            return

        # Tokenize-based name checks: skip name tokens that are part of
        # attribute access (i.e. those immediately following a '.').
        for idx, token in enumerate(tokens):
            if token.type != tokenize.NAME:
                continue

            # If previous significant token was a dot, this name is an
            # attribute (e.g. `obj.attr`) and should not be treated as a
            # standalone name for builtin-misspelling checks.
            if idx > 0:
                prev = tokens[idx - 1]
                if prev.type == tokenize.OP and prev.string == ".":
                    continue

            if token.string in PYTHON_KEYWORDS:
                continue

            if token.string in PYTHON_BUILTINS:
                continue

            if token.string in defined_names:
                continue

            matches = difflib.get_close_matches(
                token.string,
                PYTHON_BUILTINS,
                n=1,
                cutoff=0.75,
            )

            if not matches:
                continue

            item = (
                token.start[0],
                token.start[1],
                token.end[1],
            )
            if item not in seen_name:
                self._name_errors.append(item)
                seen_name.add(item)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Name):
                continue

            if not isinstance(node.ctx, ast.Load):
                continue

            if node.id in PYTHON_KEYWORDS:
                continue

            if node.id in PYTHON_BUILTINS:
                continue

            if node.id in defined_names:
                continue

            matches = difflib.get_close_matches(
                node.id,
                PYTHON_BUILTINS,
                n=1,
                cutoff=0.75,
            )

            if matches:
                item = (
                    node.lineno,
                    node.col_offset,
                    node.end_col_offset,
                )
                if item not in seen_name:
                    self._name_errors.append(item)
                    seen_name.add(item)
        self._highlight_current_line()
        self._line_number_area.update()
        # compute diagnostics count and emit signal if changed
        try:
            diag_count = len(self._syntax_errors) + len(self._keyword_errors) + len(self._name_errors)
            if diag_count != self._last_diag_count:
                self._last_diag_count = diag_count
                try:
                    self.diagnostics_changed.emit(diag_count)
                except Exception:
                    # be resilient if no listeners or signal unavailable
                    pass
        except Exception:
            pass

    def _word_under_cursor(self) -> str:
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        return cursor.selectedText()

    def _handle_auto_pairs(self, event) -> bool:
        pairs = {
            "(": ")",
            "[": "]",
            "{": "}",
            "'": "'",
            '"': '"',
        }

        cursor = self.textCursor()
        position = cursor.position()
        document_text = self.toPlainText()

        # Ignore shortcuts such as Ctrl+Z and Ctrl+C.
        if event.modifiers() & (
            Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier
        ):
            return False

        typed = event.text()

        # Delete both characters when Backspace is pressed between a pair.
        if event.key() == Qt.Key_Backspace and not cursor.hasSelection():
            if position > 0 and position < len(document_text):
                before = document_text[position - 1]
                after = document_text[position]

                if before in pairs and pairs[before] == after:
                    cursor.deletePreviousChar()
                    cursor.deleteChar()
                    self.setTextCursor(cursor)
                    return True

            return False

        # Skip an existing closing bracket or quote.
        if typed in pairs.values() and not cursor.hasSelection():
            if (
                position < len(document_text)
                and document_text[position] == typed
            ):
                cursor.movePosition(QTextCursor.Right)
                self.setTextCursor(cursor)
                return True

        # Automatically insert matching characters.
        if typed in pairs:
            closing = pairs[typed]

            if cursor.hasSelection():
                selected = cursor.selectedText()
                start = cursor.selectionStart()

                cursor.insertText(typed + selected + closing)
                cursor.setPosition(start + 1)
                cursor.setPosition(
                    start + 1 + len(selected),
                    QTextCursor.KeepAnchor,
                )
            else:
                cursor.insertText(typed + closing)
                cursor.movePosition(QTextCursor.Left)

            self.setTextCursor(cursor)
            return True

        return False

    def eventFilter(self, watched, event) -> bool:
        if hasattr(self, "_completer") and watched is self._completer.popup():
            if event.type() == QEvent.Show:
                self._reposition_completion_popup()
            elif event.type() in (QEvent.Move, QEvent.Resize) and not self._positioning_completion_popup:
                self._reposition_completion_popup()
            elif event.type() == QEvent.KeyPress and event.key() == Qt.Key_Tab:
                if self._accept_completion():
                    return True
        return super().eventFilter(watched, event)

    def _completion_popup_geometry(self) -> QRect:
        """Return the popup geometry anchored to the current cursor and clipped to the active screen."""
        popup = self._completer.popup()
        popup.adjustSize()

        model = popup.model()
        row_count = model.rowCount() if model is not None else 0
        row_height = 0
        if hasattr(popup, "sizeHintForRow"):
            try:
                row_height = popup.sizeHintForRow(0)
            except Exception:
                row_height = 0
        if row_height <= 0:
            row_height = max(1, popup.fontMetrics().height() + 8)

        width = max(1, popup.sizeHint().width())
        height = max(1, row_count * row_height + popup.frameWidth() * 2 + 8)

        cursor_rect = self.cursorRect()
        cursor_top_left = self.viewport().mapToGlobal(cursor_rect.topLeft())
        cursor_bottom_left = self.viewport().mapToGlobal(cursor_rect.bottomLeft())

        screen = QApplication.screenAt(cursor_top_left) or QApplication.primaryScreen()
        available = screen.availableGeometry()

        left = cursor_top_left.x()
        left = min(max(left, available.left()), max(available.left(), available.right() - width))

        space_above = cursor_top_left.y() - available.top()
        prefer_above = space_above >= height + 6
        top = cursor_top_left.y() - height - 4 if prefer_above else cursor_bottom_left.y() + 4

        if top + height > available.bottom():
            top = available.bottom() - height
        if top < available.top():
            top = available.top()

        return QRect(left, top, width, height)

    def _position_completion_popup(self) -> None:
        """Anchor completion suggestions to the cursor, preferring above it."""
        popup = self._completer.popup()
        if not popup.isVisible():
            return

        geometry = self._completion_popup_geometry()
        self._positioning_completion_popup = True
        try:
            popup.setGeometry(geometry)
        finally:
            self._positioning_completion_popup = False

    def _reposition_completion_popup(self, *args) -> None:
        """Keep the popup anchored while the cursor moves or the editor scrolls."""
        if self._positioning_completion_popup:
            return
        popup = self._completer.popup()
        if not popup.isVisible():
            return

        current_prefix = self._word_under_cursor()
        if not current_prefix:
            popup.hide()
            return

        self._position_completion_popup()

    def _show_completion(self) -> None:
        """Show completion anchored to the active cursor instead of Qt's default lower-edge placement."""
        cursor_rect = self.cursorRect()
        current_prefix = self._word_under_cursor()

        if not current_prefix:
            self._completer.popup().hide()
            return

        self._completer.complete(cursor_rect)

        popup = self._completer.popup()
        if popup.currentIndex().row() < 0 and popup.model().rowCount() > 0:
            popup.setCurrentIndex(popup.model().index(0, 0))
        # Qt uses the live cursor rectangle during the initial popup placement,
        # then we keep it aligned as the cursor moves or the editor scrolls.
        self._reposition_completion_popup()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        rect = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(rect.left(), rect.top(), self.line_number_area_width(), rect.height())
        )
        self._reposition_completion_popup()

    def _accept_completion(self) -> bool:
        popup = self._completer.popup()
        if not popup.isVisible():
            return False
        value = popup.currentIndex().data()
        if not value:
            return False
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        cursor.insertText(str(value))
        self.setTextCursor(cursor)
        popup.hide()
        return True

    def zoom_in(self) -> None:
        font = self.font()
        size = font.pointSize() or 11
        font.setPointSize(max(8, min(32, size + 1)))
        self.setFont(font)
        self._line_number_area.setFont(font)
        self._update_line_number_area_width(0)

    def zoom_out(self) -> None:
        font = self.font()
        size = font.pointSize() or 11
        font.setPointSize(max(8, min(32, size - 1)))
        self.setFont(font)
        self._line_number_area.setFont(font)
        self._update_line_number_area_width(0)

    def keyPressEvent(self, event) -> None:
        if self.multi_cursor_active and self._handle_multi_cursor_input(event):
            return
        if event.key() in (Qt.Key_Tab, Qt.Key_Backtab) and not (event.modifiers() & Qt.ShiftModifier):
            if self._accept_completion():
                return
        if self._handle_auto_pairs(event):
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._handle_auto_indent()
            return

        if event.key() == Qt.Key_Backspace:
            if self._handle_backspace():
                return

        if event.key() == Qt.Key.Key_D and event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.syntax_highlight_change()
            return

        """
        handle tab hihglighting and indentation. If the user presses Tab, we want insert spaces to the next indentation stop (e.g., 4 spaces). If the user presses Shift+Tab, remove spaces up to the previous indentation stop. If the user has a selection, indent or outdent all selected lines.
        """
        # Handle Tab / Shift+Tab for indentation
        if event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
            cursor = self.textCursor()

            if cursor.hasSelection():
                start = cursor.selectionStart()
                end = cursor.selectionEnd()

                start_block = self.document().findBlock(start)
                end_block = self.document().findBlock(end)

                if end == end_block.position():
                    end_block = end_block.previous()

                cursor.beginEditBlock()

                block = start_block
                while block.isValid():
                    line_cursor = QTextCursor(block)
                    line = block.text()

                    if event.modifiers() & Qt.ShiftModifier:
                        # Remove up to 4 leading spaces
                        spaces = len(line) - len(line.lstrip(" "))
                        remove_count = min(4, spaces)

                        if remove_count:
                            line_cursor.setPosition(block.position())
                            line_cursor.setPosition(
                                block.position() + remove_count,
                                QTextCursor.KeepAnchor,
                            )
                            line_cursor.removeSelectedText()
                    else:
                        # Insert 4 spaces at the beginning of each line
                        line_cursor.movePosition(
                            QTextCursor.StartOfBlock
                        )
                        line_cursor.insertText("    ")

                    if block == end_block:
                        break

                    block = block.next()

                cursor.endEditBlock()
                self.setTextCursor(cursor)
                return

            if event.modifiers() & Qt.ShiftModifier:
                # Outdent the current line
                cursor = self.textCursor()
                line = cursor.block().text()
                spaces = len(line) - len(line.lstrip(" "))
                remove_count = min(4, spaces)

                if remove_count:
                    cursor.movePosition(QTextCursor.StartOfBlock)
                    cursor.movePosition(
                        QTextCursor.Right,
                        QTextCursor.KeepAnchor,
                        remove_count,
                    )
                    cursor.removeSelectedText()

                return

            # No selection: insert spaces to the next indentation stop
            position = cursor.positionInBlock()
            indent_size = 4
            to_insert = indent_size - (position % indent_size)
            cursor.insertText(" " * to_insert)
            self.setTextCursor(cursor)
            return

        if event.modifiers() & Qt.ControlModifier:
            if event.key() in (Qt.Key_Plus, Qt.Key_Equal) and (event.modifiers() & Qt.ShiftModifier or event.text() == "+"):
                self.zoom_in()
                return
            if event.key() == Qt.Key_Minus:
                self.zoom_out()
                return

        if (event.key() == Qt.Key_Slash and event.modifiers() & Qt.ControlModifier):
            self.toggle_comment()
            return
        # allow auto-indent/backspace handling
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._handle_auto_indent()
            return

        if event.key() == Qt.Key_Backspace:
            if self._handle_backspace():
                self._completer.popup().hide()
                self._completer.popup().hide()
                return

        # handle Tab to insert spaces up to the next indent stop
        if event.key() == Qt.Key_Tab:
            cursor = self.textCursor()
            if cursor.hasSelection():
                # fallback to default behavior for selections
                super().keyPressEvent(event)
                return

            position = cursor.positionInBlock()
            indent_size = 4
            to_insert = indent_size - (position % indent_size) if indent_size else 1
            cursor.insertText(" " * to_insert)
            self.setTextCursor(cursor)
            return

        # Ctrl+Space to manually trigger completion
        if event.key() == Qt.Key_Space and event.modifiers() & Qt.ControlModifier:
            prefix = self._word_under_cursor()
            try:
                self._completer.setCompletionPrefix(prefix)
                self._show_completion()
            except Exception:
                pass
            return

        # If user typed a dot, provide attribute completions for imported modules
        if event.text() == '.':
            try:
                # find token before dot
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.Left)
                cursor.select(QTextCursor.WordUnderCursor)
                obj = cursor.selectedText()
                attrs = []
                if obj in MODULE_ATTRS:
                    attrs = MODULE_ATTRS[obj]
                elif hasattr(self, '_imports') and obj in self._imports:
                    # prefer module attrs if we imported that module
                    attrs = MODULE_ATTRS.get(obj, [])

                if attrs:
                    self._completion_model.setStringList(sorted(attrs))
                    self._completer.setCompletionPrefix('')
                    self._show_completion()
            except Exception:
                pass
            # still insert the dot
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key_Down:
            cursor = self.textCursor()
            if not cursor.block().next().isValid():
                cursor.movePosition(QTextCursor.EndOfBlock)
                self.setTextCursor(cursor)
                return

        super().keyPressEvent(event)

        # after inserting a character, if it's part of an identifier, show completions
        last = event.text()
        if last and (last.isalpha() or last == "_" or last.isdigit()):
            prefix = self._word_under_cursor()
            if prefix:
                try:
                    self._completer.setCompletionPrefix(prefix)
                    self._show_completion()
                except Exception:
                    pass

    # line number gutter
    def set_line_number_mode(self, mode: str) -> None:
        if mode not in {"absolute", "relative", "hybrid"}:
            raise ValueError(f"Unknown line-number mode: {mode}")
        self._line_number_mode = mode
        self._line_number_area.update()

    def line_number_for(self, line_number: int, current_line: int) -> int:
        if self._line_number_mode == "relative":
            return abs(line_number - current_line)
        if self._line_number_mode == "hybrid":
            return line_number if line_number == current_line else abs(line_number - current_line)
        return line_number

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_area_width(self, _new_block_count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#1e1e1e"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        error_lines = self._error_line_numbers()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                absolute_line = block_number + 1
                current_line = self.textCursor().blockNumber() + 1
                line_number = self.line_number_for(absolute_line, current_line)
                painter.setPen(QColor("#f44747" if line_number in error_lines else "#858585"))
                painter.drawText(
                    0, int(top), self._line_number_area.width() - 6, self.fontMetrics().height(),
                    Qt.AlignRight, str(line_number),
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def _highlight_current_line(self) -> None:
        """Highlight the current line and any syntax error."""

        selections = []

        # current line
        current_selection = QTextEdit.ExtraSelection()
        current_selection.format.setBackground(QColor("#2a2d2e"))
        current_selection.format.setProperty(
            QTextFormat.FullWidthSelection,
            True,
        )

        current_selection.cursor = self.textCursor()
        current_selection.cursor.clearSelection()

        selections.append(current_selection)

        # syntax errors
        for line, start, end in self._syntax_errors:
            block = self.document().findBlockByLineNumber(line - 1)

            if not block.isValid():
                continue

            error_selection = QTextEdit.ExtraSelection()

            error_selection.format.setUnderlineColor(
                QColor("#f44747")
            )
            error_selection.format.setUnderlineStyle(
                QTextCharFormat.WaveUnderline
            )

            start = max(0, start - 1)

            if end is not None:
                end = max(start + 1, end - 1)
            else:
                end = min(start + 1, len(block.text()))

            cursor = QTextCursor(block)
            cursor.setPosition(block.position() + start)
            cursor.setPosition(
                block.position() + end,
                QTextCursor.KeepAnchor,
            )

            error_selection.cursor = cursor
            selections.append(error_selection)

        # keyword errors
        for line, start, end in self._keyword_errors:
            block = self.document().findBlockByLineNumber(line - 1)

            if not block.isValid():
                continue

            error_selection = QTextEdit.ExtraSelection()

            error_selection.format.setUnderlineColor(
                QColor("#f44747")
            )
            error_selection.format.setUnderlineStyle(
                QTextCharFormat.WaveUnderline
            )

            cursor = QTextCursor(block)
            cursor.setPosition(block.position() + start)
            cursor.setPosition(
                block.position() + end,
                QTextCursor.KeepAnchor,
            )

            error_selection.cursor = cursor
            selections.append(error_selection)

        # name errors
        for line, start, end in self._name_errors:
            block = self.document().findBlockByLineNumber(line - 1)

            if not block.isValid():
                continue

            error_selection = QTextEdit.ExtraSelection()

            error_selection.format.setUnderlineColor(
                QColor("#f44747")
            )
            error_selection.format.setUnderlineStyle(
                QTextCharFormat.WaveUnderline
            )

            cursor = QTextCursor(block)
            cursor.setPosition(block.position() + start)
            cursor.setPosition(
                block.position() + end,
                QTextCursor.KeepAnchor,
            )

            error_selection.cursor = cursor
            selections.append(error_selection)

        self.setExtraSelections(selections)
        self._line_number_area.update()

    # # auto indentation
    # def keyPressEvent(self, event) -> None:
    #     i
    def contextMenuEvent(self, event) -> None:
        """Show a lightweight context (right-click) menu with common actions."""
        menu = QMenu(self)

        undo = QAction("Undo", self)
        undo.triggered.connect(self.undo)
        menu.addAction(undo)

        redo = QAction("Redo", self)
        redo.triggered.connect(self.redo)
        menu.addAction(redo)

        menu.addSeparator()

        cut = QAction("Cut", self)
        cut.triggered.connect(self.cut)
        menu.addAction(cut)

        copy = QAction("Copy", self)
        copy.triggered.connect(self.copy)
        menu.addAction(copy)

        paste = QAction("Paste", self)
        paste.triggered.connect(self.paste)
        menu.addAction(paste)

        menu.addSeparator()

        select_all = QAction("Select All", self)
        select_all.triggered.connect(self.selectAll)
        menu.addAction(select_all)

        find = QAction("Find", self)
        def _open_find():
            w = self.window()
            if hasattr(w, "_open_search"):
                try:
                    w._open_search()
                except Exception:
                    pass

        find.triggered.connect(_open_find)
        menu.addAction(find)

        menu.exec(event.globalPos())

    def _handle_backspace(self) -> bool:
        cursor = self.textCursor()

        if cursor.hasSelection():
            return False

        position = cursor.positionInBlock()
        line = cursor.block().text()

        # only handle backspace inside indentation shish
        if position == 0:
            return False

        before_cursor = line[:position]

        if not before_cursor.isspace():
            return False

        # compute how many spaces to remove to go back to previous
        # indentation stop (e.g., 4 spaces). Only remove actual space
        # characters that are present immediately before the cursor so
        # we do not delete characters from the previous line.
        indent_size = 4
        try:
            rem = position % indent_size
            to_remove = rem if rem != 0 else indent_size
        except Exception:
            to_remove = 1

        # limit to available trailing spaces in the current block
        trailing_spaces = len(before_cursor) - len(before_cursor.rstrip(" "))
        if trailing_spaces == 0:
            return False

        to_remove = min(to_remove, trailing_spaces)

        for _ in range(to_remove):
            cursor.deletePreviousChar()

        self.setTextCursor(cursor)

        return True
    def _handle_auto_indent(self) -> None:
        """
        When the user presses Enter, keep the same indentation as the
        current line, and add one extra indent level if the line ends
        with a colon (e.g. `if x:`, `def foo():`).

        This is intentionally simple — it looks only at the current
        line's text, not the whole file's structure, on purpose.
        """
        import re

        cursor = self.textCursor()
        current_block = cursor.block()
        current_line = current_block.text()

        # if the current line is empty or only whitespace, try to base the
        # indentation on the previous non-empty line so pressing Enter on a
        # blank indented line keeps the expected nested indentation.
        if not current_line.strip():
            prev = current_block.previous()
            while prev.isValid() and not prev.text().strip():
                prev = prev.previous()
            base_line = prev.text() if prev.isValid() else ""
        else:
            base_line = current_line

        m = re.match(r"^(\s*)", base_line)
        base_indent = m.group(1) if m else ""

        # if the (base) line ends with a colon, add one indent level
        extra = "    " if base_line.rstrip().endswith(":") else ""

        new_indent = base_indent + extra

        cursor.insertText("\n" + new_indent)
        self.setTextCursor(cursor)
    def toggle_comment(self):
        cursor = self.textCursor()

        start_block = self.document().findBlock(
            cursor.selectionStart()
        )
        end_block = self.document().findBlock(
            cursor.selectionEnd()
        )

        # If the selection ends at the beginning of a line,
        # don't include that final line.
        if (
            cursor.hasSelection()
            and cursor.selectionEnd() == end_block.position()
        ):
            end_block = end_block.previous()

        # Determine whether all non-empty lines are commented.
        blocks = []
        block = start_block

        while block.isValid():
            blocks.append(block)

            if block == end_block:
                break

            block = block.next()

        non_empty_lines = [
            block.text() for block in blocks if block.text().strip()
        ]

        uncomment = bool(non_empty_lines) and all(
            line.lstrip().startswith("#")
            for line in non_empty_lines
        )

        cursor.beginEditBlock()

        for block in blocks:
            line = block.text()

            if not line.strip():
                continue

            line_cursor = QTextCursor(block)
            line_cursor.movePosition(QTextCursor.StartOfBlock)

            if uncomment:
                # Remove the comment marker and one optional space.
                stripped = line.lstrip()
                indent = len(line) - len(stripped)
                line_cursor.movePosition(
                    QTextCursor.Right,
                    QTextCursor.MoveAnchor,
                    indent,
                )
                line_cursor.deleteChar()  # Remove '#'

                if line_cursor.block().text()[
                    line_cursor.positionInBlock():
                ].startswith(" "):
                    line_cursor.deleteChar()
            else:
                # Insert the comment marker after indentation.
                indent = len(line) - len(line.lstrip())
                line_cursor.movePosition(
                    QTextCursor.Right,
                    QTextCursor.MoveAnchor,
                    indent,
                )
                line_cursor.insertText("# ")

        cursor.endEditBlock()

        # Keep the affected lines selected.
        selection = QTextCursor(start_block)
        selection.setPosition(
            blocks[-1].position() + blocks[-1].length() - 1,
            QTextCursor.KeepAnchor,
        )
        self.setTextCursor(selection)
    
    def _handle_multi_cursor_input(self, event) -> bool:
        if event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
            return False
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab, Qt.Key_Backtab):
            return False
        text = event.text()
        if not text and event.key() != Qt.Key_Backspace:
            return False

        previous = self._multi_cursor_replacement
        replacement = previous[:-1] if event.key() == Qt.Key_Backspace else previous + text
        current_length = len(previous) or self._multi_cursor_original_length
        position_delta = 0 if not previous else len(previous) - self._multi_cursor_original_length

        document = self.document()
        edit = QTextCursor(document)
        edit.beginEditBlock()
        for index in reversed(range(len(self._multi_cursor_starts))):
            start = self._multi_cursor_starts[index] + index * position_delta
            edit.setPosition(start)
            edit.setPosition(start + current_length, QTextCursor.KeepAnchor)
            edit.insertText(replacement)
        edit.endEditBlock()
        self._multi_cursor_replacement = replacement
        if not replacement:
            self.multi_cursor_active = False
            self.setExtraSelections([])
        else:
            self._highlight_multi_cursor_occurrences()
        return True

    def _highlight_multi_cursor_occurrences(self) -> None:
        selections = []
        document = self.document()
        token = self._multi_cursor_replacement or self._multi_cursor_word
        cursor = QTextCursor(document)
        while True:
            cursor = document.find(token, cursor)
            if cursor.isNull():
                break
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("#4C5BFF"))
            fmt.setForeground(Qt.GlobalColor.white)
            selection.format = fmt
            selections.append(selection)
        self.setExtraSelections(selections)

    def syntax_highlight_change(self):
        """Select every occurrence for synchronized replacement editing."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            word = cursor.selectedText()
        else:
            cursor.select(QTextCursor.WordUnderCursor)
            word = cursor.selectedText()
        if not word:
            return
        self._multi_cursor_word = word
        self._multi_cursor_replacement = ""
        self._multi_cursor_original_length = len(word)
        self._multi_cursor_starts = []
        search = QTextCursor(self.document())
        while True:
            search = self.document().find(word, search)
            if search.isNull():
                break
            self._multi_cursor_starts.append(search.selectionStart())
        self.multi_cursor_active = True
        self._highlight_multi_cursor_occurrences()
