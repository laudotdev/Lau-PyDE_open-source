import ast
import difflib
import re
import tokenize
from io import StringIO
from pathlib import Path
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

SOURCE_KEYWORDS = {
    "html": ["a", "article", "aside", "body", "button", "div", "doctype", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "head", "header", "html", "img", "input", "label", "li", "link", "main", "meta", "nav", "ol", "option", "p", "section", "script", "select", "span", "style", "table", "td", "textarea", "th", "title", "tr", "ul"],
    "css": ["align-items", "background", "border", "color", "display", "flex", "font", "grid", "height", "justify-content", "margin", "padding", "position", "width"],
    "javascript": ["as", "async", "await", "break", "case", "catch", "class", "const", "continue", "debugger", "default", "delete", "do", "else", "export", "extends", "false", "finally", "for", "from", "function", "if", "import", "in", "instanceof", "let", "new", "null", "of", "return", "static", "super", "switch", "this", "throw", "true", "try", "typeof", "var", "void", "while", "with", "yield"],
    "markdown": ["heading", "link", "image", "code", "list", "quote"],
    "json": ["false", "null", "true"],
    "yaml": ["false", "no", "null", "true", "yes"],
    "toml": ["false", "true"],
    "c": ["auto", "break", "case", "char", "const", "continue", "default", "do", "double", "else", "enum", "extern", "float", "for", "if", "int", "long", "return", "short", "sizeof", "static", "struct", "switch", "typedef", "union", "unsigned", "void", "while"],
    "cpp": ["auto", "bool", "break", "case", "catch", "class", "const", "continue", "default", "delete", "else", "false", "for", "if", "include", "int", "namespace", "new", "nullptr", "public", "return", "std", "struct", "switch", "template", "this", "true", "try", "using", "void", "while"],
    "java": ["abstract", "boolean", "break", "byte", "case", "catch", "char", "class", "const", "continue", "default", "do", "double", "else", "extends", "final", "finally", "float", "for", "if", "implements", "import", "instanceof", "int", "interface", "long", "new", "package", "private", "protected", "public", "return", "static", "super", "switch", "this", "throw", "throws", "try", "void", "while"],
    "go": ["break", "case", "chan", "const", "continue", "default", "defer", "else", "fallthrough", "for", "func", "go", "goto", "if", "import", "interface", "map", "package", "range", "return", "select", "struct", "switch", "type", "var"],
    "rust": ["as", "async", "await", "break", "const", "continue", "crate", "else", "enum", "extern", "false", "fn", "for", "if", "impl", "in", "let", "loop", "match", "mod", "move", "mut", "pub", "ref", "return", "self", "static", "struct", "super", "trait", "true", "type", "unsafe", "use", "where", "while"],
}

CSS_PROPERTIES = """
accent-color align-content align-items align-self all animation animation-composition
animation-delay animation-direction animation-duration animation-fill-mode animation-iteration-count
animation-name animation-play-state animation-timing-function appearance aspect-ratio backdrop-filter
backface-visibility background background-attachment background-blend-mode background-clip
background-color background-image background-origin background-position background-position-x
background-position-y background-repeat background-size block-size border border-block border-block-color
border-block-end border-block-end-color border-block-end-style border-block-end-width border-block-start
border-block-start-color border-block-start-style border-block-start-width border-block-style
border-block-width border-bottom border-bottom-color border-bottom-left-radius border-bottom-right-radius
border-bottom-style border-bottom-width border-collapse border-color border-image border-image-outset
border-image-repeat border-image-slice border-image-source border-image-width border-inline border-inline-color
border-inline-end border-inline-end-color border-inline-end-style border-inline-end-width border-inline-start
border-inline-start-color border-inline-start-style border-inline-start-width border-inline-style
border-inline-width border-left border-left-color border-left-style border-left-width border-radius border-right
border-right-color border-right-style border-right-width border-spacing border-style border-top border-top-color
border-top-left-radius border-top-right-radius border-top-style border-top-width border-width bottom box-shadow
box-sizing break-after break-before break-inside caption-side caret-color clear clip clip-path color color-scheme
column-count column-fill column-gap column-rule column-rule-color column-rule-style column-rule-width column-span
column-width columns contain contain-intrinsic-size container container-name container-type content
content-visibility cursor direction display empty-cells filter flex flex-basis flex-direction flex-flow flex-grow
flex-shrink flex-wrap float font font-family font-feature-settings font-kerning font-optical-sizing font-size
font-size-adjust font-stretch font-style font-variant font-variant-caps font-weight gap grid grid-area grid-auto-columns
grid-auto-flow grid-auto-rows grid-column grid-column-end grid-column-gap grid-column-start grid-gap grid-row
grid-row-end grid-row-gap grid-row-start grid-template grid-template-areas grid-template-columns grid-template-rows
height hyphens image-rendering inline-size inset inset-block inset-block-end inset-block-start inset-inline
inset-inline-end inset-inline-start isolation justify-content justify-items justify-self left letter-spacing line-break
line-height list-style list-style-image list-style-position list-style-type margin margin-block margin-block-end
margin-block-start margin-bottom margin-inline margin-inline-end margin-inline-start margin-left margin-right
margin-top mask max-block-size max-height max-inline-size max-width min-block-size min-height min-inline-size min-width
 object-fit object-position opacity order orphans outline outline-color outline-offset outline-style outline-width
overflow overflow-anchor overflow-wrap overflow-x overflow-y overscroll-behavior overscroll-behavior-block
overscroll-behavior-inline overscroll-behavior-x overscroll-behavior-y padding padding-block padding-block-end
padding-block-start padding-bottom padding-inline padding-inline-end padding-inline-start padding-left padding-right
padding-top page-break-after page-break-before page-break-inside perspective perspective-origin place-content
place-items place-self pointer-events position print-color-adjust quotes resize right rotate row-gap scale scroll-behavior
scroll-margin scroll-padding scroll-snap-align scroll-snap-stop scroll-snap-type scrollbar-color scrollbar-gutter
scrollbar-width shape-outside tab-size table-layout text-align text-align-last text-decoration text-decoration-color
text-decoration-line text-decoration-style text-indent text-overflow text-rendering text-shadow text-transform top
touch-action transform transform-origin transform-style transition transition-delay transition-duration transition-property
transition-timing-function translate unicode-bidi user-select vertical-align visibility white-space widows width
will-change word-break word-spacing word-wrap writing-mode z-index
""".split()

JAVASCRIPT_GLOBALS = """
AggregateError Array ArrayBuffer Atomics BigInt BigInt64Array BigUint64Array Boolean DataView Date Error EvalError
FinalizationRegistry Float32Array Float64Array Function Infinity Int8Array Int16Array Int32Array Intl JSON Map Math
NaN Number Object Promise Proxy RangeError ReferenceError Reflect RegExp Set SharedArrayBuffer String Symbol SyntaxError
TypeError URIError URL URLSearchParams WeakMap WeakRef WeakSet WebAssembly XMLHttpRequest alert atob btoa clearInterval
clearTimeout console decodeURI decodeURIComponent document encodeURI encodeURIComponent escape eval fetch globalThis history
isFinite isNaN location localStorage name navigator parseFloat parseInt prompt sessionStorage setInterval setTimeout
undefined unescape window
""".split()

JAVASCRIPT_MEMBERS = {
    "document": """addEventListener adoptNode append createAttribute createComment createDocumentFragment createElement
        createElementNS createEvent createTextNode doctype documentElement documentURI getElementById getElementsByClassName
        getElementsByName getElementsByTagName getElementsByTagNameNS importNode querySelector querySelectorAll readyState
        removeEventListener title body head activeElement cookie forms images links scripts styleSheets visibilityState""",
    "window": """addEventListener alert atob blur btoa cancelAnimationFrame clearInterval clearTimeout close confirm
        devicePixelRatio document focus getComputedStyle getSelection history innerHeight innerWidth localStorage location
        matchMedia moveBy moveTo name navigator open outerHeight outerWidth pageXOffset pageYOffset parent print prompt
        requestAnimationFrame resizeBy resizeTo screen screenX screenY scroll scrollBy scrollTo self sessionStorage setInterval
        setTimeout stop top""",
    "element": """addEventListener append appendChild animate attachShadow before blur click closest compareDocumentPosition
        contains getAttribute getAttributeNames getBoundingClientRect getElementsByClassName getElementsByTagName hasAttribute
        insertAdjacentElement insertAdjacentHTML insertAdjacentText matches prepend querySelector querySelectorAll remove
        removeAttribute removeChild removeEventListener replaceChildren replaceWith scrollIntoView setAttribute toggleAttribute
        after children classList className clientHeight clientWidth dataset firstChild firstElementChild id innerHTML innerText
        isConnected lastChild nextElementSibling nextSibling outerHTML parentElement parentNode previousElementSibling
        previousSibling style tagName textContent""",
    "console": "assert clear count debug dir error group groupCollapsed groupEnd info log table time timeEnd trace warn",
    "navigator": "clipboard cookieEnabled geolocation language languages maxTouchPoints onLine platform userAgent",
    "location": "assign hash host hostname href origin pathname port protocol reload replace search toString",
    "history": "back forward go length pushState replaceState scrollRestoration state",
    "localStorage": "clear getItem key length removeItem setItem",
    "sessionStorage": "clear getItem key length removeItem setItem",
    "JSON": "parse stringify",
    "Math": """abs acos acosh asin asinh atan atan2 atanh cbrt ceil clz32 cos cosh exp expm1 floor fround hypot imul log
        log10 log1p log2 max min pow random round sign sin sinh sqrt tan tanh trunc E LN10 LN2 LOG10E LOG2E PI SQRT1_2 SQRT2""",
    "Array": "from fromAsync isArray of",
    "Object": """assign create defineProperties defineProperty entries freeze fromEntries getOwnPropertyDescriptor
        getOwnPropertyDescriptors getOwnPropertyNames getOwnPropertySymbols getPrototypeOf hasOwn is isExtensible isFrozen
        isSealed keys preventExtensions seal setPrototypeOf values""",
    "String": "fromCharCode fromCodePoint raw",
    "Number": """isFinite isInteger isNaN isSafeInteger parseFloat parseInt MAX_SAFE_INTEGER MAX_VALUE MIN_SAFE_INTEGER
        MIN_VALUE NaN NEGATIVE_INFINITY POSITIVE_INFINITY""",
    "Promise": "all allSettled any race reject resolve withResolvers",
}
JAVASCRIPT_MEMBERS = {
    name: " ".join(value.split()) for name, value in JAVASCRIPT_MEMBERS.items()
}

EXTENSION_LANGUAGES = {
    ".htm": "html", ".html": "html", ".css": "css",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".md": "markdown", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp",
    ".cxx": "cpp", ".hh": "cpp", ".hpp": "cpp", ".java": "java",
    ".go": "go", ".rs": "rust",
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


class SourceHighlighter(QSyntaxHighlighter):
    def __init__(self, document, language: str):
        super().__init__(document)
        self.language = language
        self._rules = []

        def add(
            pattern: str, color: str, bold: bool = False, capture_group: int = 0
        ) -> None:
            text_format = QTextCharFormat()
            text_format.setForeground(QColor(color))
            if bold:
                text_format.setFontWeight(QFont.Bold)
            self._rules.append((QRegularExpression(pattern), text_format, capture_group))

        keywords = SOURCE_KEYWORDS.get(language, [])
        if keywords and language != "html":
            keyword_color = {
                "css": "#45c7b8",
                "javascript": "#ff6b9d",
            }.get(language, "#c586c0")
            add(r"\b(?:" + "|".join(re.escape(word) for word in keywords) + r")\b", keyword_color, True)
        if language == "javascript":
            add(
                r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)",
                "#f2cc60",
                capture_group=1,
            )
            globals_pattern = "|".join(
                re.escape(name) for name in sorted(JAVASCRIPT_GLOBALS)
            )
            add(r"\b(?:" + globals_pattern + r")\b", "#4fc1ff")
            add(
                r"\b(?!(?:"
                + "|".join(re.escape(word) for word in keywords)
                + r")\b)([A-Za-z_$][\w$]*)(?=\s*\()",
                "#dcdcaa",
                capture_group=1,
            )
            add(
                r"\bfunction\s*\*?\s+([A-Za-z_$][\w$]*)",
                "#82aaff",
                True,
                capture_group=1,
            )
            add(
                r"\.\s*([A-Za-z_$][\w$]*)",
                "#9cdcfe",
                capture_group=1,
            )
            add(
                r"\.\s*([A-Za-z_$][\w$]*)(?=\s*\()",
                "#4ec9b0",
                capture_group=1,
            )
            add(
                r"\b([A-Za-z_$][\w$]*)(?=\s*:)",
                "#9cdcfe",
                capture_group=1,
            )
            add(r"===|!==|=>|==|!=|<=|>=|&&|\|\||\?\?|[-+*/%=&|<>!?:]", "#c586c0")
        number_color = {"css": "#b8df6f", "javascript": "#b8df6f"}.get(language, "#b5cea8")
        string_color = {"css": "#f4a261", "javascript": "#ffd580"}.get(language, "#ce9178")
        comment_color = {"css": "#77c7a6", "javascript": "#77c7a6"}.get(language, "#6a9955")
        add(r"\b\d+(?:\.\d+)?\b", number_color)
        add(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|`[^`]*`", string_color)
        if language == "html":
            add(r"</?|/?>", "#808080")
            add(r"</?([A-Za-z][\w:-]*)", "#4fc3f7", True, capture_group=1)
            add(
                r"\s+([A-Za-z_:][\w:.-]*)(?=\s*(?:=|/?>))",
                "#9cdcfe",
                capture_group=1,
            )
            add(r"<!DOCTYPE\b", "#c586c0", True)
            add(r"&(?:#[0-9]+|#x[0-9a-fA-F]+|[A-Za-z][\w]+);", "#d7ba7d")
            self._html_comment_format = QTextCharFormat()
            self._html_comment_format.setForeground(QColor("#77c7a6"))
        if language in {"javascript", "css", "c", "cpp", "java"}:
            add(r"//[^\n]*|/\*.*?\*/", comment_color)
        if language == "css":
            add(r"^[ \t]*[-\w]+(?=\s*:)", "#45c7b8")
            add(r"^[^{]+(?=\s*\{)", "#ff9f68")
            add(r"@[\w-]+", "#d8a7ff", True)
        elif language == "markdown":
            add(r"^\s{0,3}#{1,6}\s+.*$", "#569cd6", True)
            add(r"`[^`]+`", "#ce9178")
            add(r"!?\[[^]]*\]\([^)]*\)", "#4ec9b0")
        elif language in {"json", "yaml", "toml"}:
            add(r"^[ \t]*[\w.-]+(?=\s*:|\s*=)", "#9cdcfe")
            add(r"\b(?:true|false|null)\b", "#569cd6", True)

    def highlightBlock(self, text: str) -> None:
        for pattern, text_format, capture_group in self._rules:
            matches = pattern.globalMatch(text)
            while matches.hasNext():
                match = matches.next()
                if capture_group:
                    start = match.capturedStart(capture_group)
                    length = match.capturedLength(capture_group)
                else:
                    start = match.capturedStart()
                    length = match.capturedLength()
                if start >= 0 and length > 0:
                    self.setFormat(start, length, text_format)
        if self.language == "html":
            comment_start = (
                0 if self.previousBlockState() == 1 else text.find("<!--")
            )
            while comment_start >= 0:
                comment_end = text.find("-->", comment_start)
                if comment_end < 0:
                    self.setFormat(
                        comment_start,
                        len(text) - comment_start,
                        self._html_comment_format,
                    )
                    self.setCurrentBlockState(1)
                    break
                self.setFormat(
                    comment_start,
                    comment_end + 3 - comment_start,
                    self._html_comment_format,
                )
                comment_start = text.find("<!--", comment_end + 3)
            else:
                self.setCurrentBlockState(0)


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
        self._source_diagnostics: list[str] = []
        self._language = "python"
        self._is_python_file = True

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
        self._completion_replace_start: int | None = None
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

    def set_file_path(self, path: str | None) -> None:
        suffix = Path(path).suffix.lower() if path else ".py"
        language = EXTENSION_LANGUAGES.get(suffix, "python" if suffix == ".py" else "text")
        if language != self._language:
            self._highlighter.setDocument(None)
            self._highlighter.deleteLater()
            self._highlighter = (
                PythonHighlighter(self.document())
                if language == "python"
                else SourceHighlighter(self.document(), language)
            )
            self._language = language
        self._is_python_file = language == "python"
        self._check_errors()

    def get_error_messages(self) -> list[str]:
        """Return human-readable error messages for all current issues."""
        self._check_errors()

        if not self._is_python_file:
            return self._source_diagnostics.copy()

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
        self._source_diagnostics = []

        if not self._is_python_file:
            words = set(re.findall(r"\b[A-Za-z_$][\w$]*\b", code))
            if self._language == "css":
                words.update(CSS_PROPERTIES)
            elif self._language == "javascript":
                words.update(JAVASCRIPT_GLOBALS)
                words.update(
                    member
                    for members in JAVASCRIPT_MEMBERS.values()
                    for member in members.split()
                )
                words.update({"addEventListener", "removeEventListener"})
            else:
                words.update(SOURCE_KEYWORDS.get(self._language, []))
            self._completion_model.setStringList(sorted(words))
            self._source_diagnostics = self._diagnose_source(code)
            self._highlight_current_line()
            self._line_number_area.update()
            diag_count = len(self._source_diagnostics)
            if diag_count != self._last_diag_count:
                self._last_diag_count = diag_count
                self.diagnostics_changed.emit(diag_count)
            return

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

    def _diagnose_source(self, code: str) -> list[str]:
        diagnostics = []
        if self._language == "markdown":
            fences = re.findall(r"(?m)^\s*(```+|~~~+)", code)
            if len(fences) % 2:
                diagnostics.append("Unclosed Markdown code fence.")
        elif self._language == "html":
            void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
            optional_close = {"dd", "dt", "li", "option", "optgroup", "p", "td", "th", "tr"}
            stack = []
            for match in re.finditer(r"</?([A-Za-z][\w:-]*)\b[^>]*>", code):
                tag = match.group(1).lower()
                raw_tag = match.group(0)
                line = code.count("\n", 0, match.start()) + 1
                if raw_tag.startswith("</"):
                    if stack and stack[-1][0] == tag:
                        stack.pop()
                    elif tag in optional_close and any(item[0] == tag for item in stack):
                        while stack and stack[-1][0] != tag:
                            stack.pop()
                        if stack:
                            stack.pop()
                    else:
                        diagnostics.append(f"Line {line}: Unexpected closing </{tag}> tag.")
                elif tag not in void_tags and not raw_tag.rstrip().endswith("/>"):
                    stack.append((tag, line))
            for tag, line in stack:
                diagnostics.append(f"Line {line}: <{tag}> is not closed.")
        elif self._language in {"css", "javascript"}:
            source = re.sub(
                r"(?s)/\*.*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`",
                " ",
                code,
            )
            source = re.sub(r"//[^\n]*", " ", source)
            pairs = {"(": ")", "[": "]", "{": "}"}
            stack = []
            for index, character in enumerate(source):
                line = source.count("\n", 0, index) + 1
                if character in pairs:
                    stack.append((character, line))
                elif character in pairs.values():
                    if not stack or pairs[stack[-1][0]] != character:
                        diagnostics.append(f"Line {line}: Unexpected '{character}'.")
                        break
                    stack.pop()
            if stack:
                character, line = stack[-1]
                diagnostics.append(f"Line {line}: '{pairs[character]}' is missing.")
        return diagnostics

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

    def _expand_html_boilerplate(self) -> bool:
        if self.toPlainText().strip() != "!":
            return False

        template = (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="UTF-8">\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            "  <title></title>\n"
            "</head>\n"
            "<body>\n"
            "\n"
            "</body>\n"
            "</html>"
        )
        self.setPlainText(template)
        cursor = self.textCursor()
        cursor.setPosition(template.index("\n\n</body>") + 1)
        self.setTextCursor(cursor)
        return True

    def _expand_html_abbreviation(self) -> bool:
        cursor = self.textCursor()
        line = cursor.block().text()
        match = re.fullmatch(r"(\s*)([a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?)\s*", line, re.IGNORECASE)
        if not match:
            return False

        indentation, abbreviation = match.groups()
        abbreviation = abbreviation.lower().split(":", 1)
        tag = abbreviation[0]
        variant = abbreviation[1] if len(abbreviation) == 2 else None
        void_tags = {
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr",
        }
        known_tags = set(SOURCE_KEYWORDS["html"]) | {
            "address", "blockquote", "caption", "code", "dd", "del", "details",
            "dialog", "dl", "dt", "fieldset", "figcaption", "figure", "iframe",
            "em", "i", "ins", "kbd", "legend", "mark", "menu", "noscript", "optgroup",
            "output", "pre", "progress", "small", "summary", "sup", "sub",
            "strong", "time", "u", "video", "audio", "canvas", "template", "thead", "tbody",
            "tfoot", "colgroup", "datalist", "picture", "source", "track",
            "b", "abbr", "acronym", "cite", "data", "dfn", "meter", "ruby", "s", "samp", "var",
            "marquee", "portal", "search", "slot", "svg",
        }
        if tag not in known_tags:
            return False

        if tag == "link" and variant in (None, "css"):
            expansion = '<link rel="stylesheet" href="style.css">'
            cursor_offset = expansion.index("style.css")
        elif tag == "input" and variant:
            allowed_types = {
                "button", "checkbox", "color", "date", "datetime-local", "email",
                "file", "hidden", "image", "month", "number", "password", "radio",
                "range", "reset", "search", "submit", "tel", "text", "time", "url", "week",
            }
            if variant not in allowed_types:
                return False
            expansion = f'<input type="{variant}" class="">'
            cursor_offset = expansion.index('class="') + len('class="')
        elif variant:
            return False
        elif tag in void_tags:
            if tag == "img":
                expansion = '<img src="" alt="">'
            elif tag == "input":
                expansion = '<input type="text" class="">'
            elif tag == "link":
                expansion = '<link rel="stylesheet" href="style.css">'
            else:
                expansion = f"<{tag}>"
            cursor_offset = len(expansion)
        else:
            expansion = f"<{tag}></{tag}>"
            cursor_offset = len(tag) + 2

        block = cursor.block()
        block_position = block.position()
        cursor.setPosition(block.position())
        cursor.setPosition(block.position() + len(line), QTextCursor.KeepAnchor)
        cursor.insertText(indentation + expansion)
        cursor.setPosition(block_position + len(indentation) + cursor_offset)
        self.setTextCursor(cursor)
        return True

    def _complete_html_tag(self) -> bool:
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False

        before_cursor = cursor.block().text()[:cursor.positionInBlock()]
        match = re.search(r"<([A-Za-z][\w:-]*)(?:\s+[^<>]*)?$", before_cursor)
        if not match:
            return False

        typed_tag = match.group(1)
        tag = typed_tag
        if self._completer.popup().isVisible():
            candidate = self._completer.popup().currentIndex().data()
            if candidate and str(candidate).lower().startswith(typed_tag.lower()):
                tag = str(candidate)
        if tag.lower() in {
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr",
        }:
            return False

        closing_tag = f"</{tag}>"
        replace_start = cursor.block().position() + match.start()
        replace_end = cursor.position()
        cursor.setPosition(replace_start)
        cursor.setPosition(replace_end, QTextCursor.KeepAnchor)
        cursor.insertText(f"<{tag}>{closing_tag}")
        cursor.setPosition(replace_start + len(tag) + 2)
        self.setTextCursor(cursor)
        return True

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
            self._completer.setCurrentRow(0)
            value = self._completer.currentCompletion()
        if not value:
            return False
        return self._insert_completion(str(value))

    def _insert_completion(self, value: str) -> bool:
        cursor = self.textCursor()
        if self._completion_replace_start is not None:
            cursor.setPosition(self._completion_replace_start)
            cursor.setPosition(self.textCursor().position(), QTextCursor.KeepAnchor)
        else:
            cursor.select(QTextCursor.WordUnderCursor)
        cursor.insertText(value)
        self.setTextCursor(cursor)
        self._completion_replace_start = None
        self._completer.popup().hide()
        return True

    def _accept_language_prefix(self) -> bool:
        if self._language not in {"css", "javascript"}:
            return False
        self._update_language_completions()
        prefix = self._completer.completionPrefix()
        if len(prefix) < 2:
            return False
        matches = self._completer.completionModel()
        if matches.rowCount() == 0:
            return False
        candidate = matches.index(0, 0).data()
        if not candidate or str(candidate).lower() == prefix.lower():
            return False
        return self._insert_completion(str(candidate))

    def _update_language_completions(self) -> None:
        if self._language not in {"css", "javascript"}:
            return
        cursor = self.textCursor()
        line_prefix = cursor.block().text()[:cursor.positionInBlock()]
        if self._language == "javascript":
            member_match = re.search(r"\b([A-Za-z_$][\w$]*)\.([\w$]*)$", line_prefix)
            if member_match:
                object_name = member_match.group(1)
                members = JAVASCRIPT_MEMBERS.get(object_name)
                if members:
                    self._completion_replace_start = cursor.position() - len(member_match.group(2))
                    self._completion_model.setStringList(sorted(set(members.split())))
                    self._completer.setCompletionPrefix(member_match.group(2))
                    return
        if self._language == "css":
            prefix_match = re.search(r"[\w-]*$", line_prefix)
            prefix = prefix_match.group(0) if prefix_match else ""
            self._completion_replace_start = cursor.position() - len(prefix)
            candidates = CSS_PROPERTIES
        else:
            prefix = self._word_under_cursor()
            self._completion_replace_start = cursor.position() - len(prefix)
            candidates = JAVASCRIPT_GLOBALS
        if self._language == "javascript":
            candidates = set(candidates) | {
                member
                for members in JAVASCRIPT_MEMBERS.values()
                for member in members.split()
            } | {"addEventListener", "removeEventListener"}
        self._completion_model.setStringList(sorted(set(candidates)))
        self._completer.setCompletionPrefix(prefix)

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
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and self._completer.popup().isVisible():
            if self._accept_completion():
                return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and self._accept_language_prefix():
            return
        if self._language == "html":
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab) and self.toPlainText().strip() == "!":
                if self._expand_html_boilerplate():
                    return
            if event.key() == Qt.Key_Tab and not (event.modifiers() & Qt.ShiftModifier):
                if self._complete_html_tag():
                    return
            if event.text() == ">" and self._complete_html_tag():
                return
        if event.key() in (Qt.Key_Tab, Qt.Key_Backtab) and not (event.modifiers() & Qt.ShiftModifier):
            if self._language == "html" and self._expand_html_abbreviation():
                return
            if self._accept_completion():
                return
            if self._accept_language_prefix():
                return
        if self._language in {"javascript", "css", "c", "cpp", "java", "go", "rust"} and event.text() == "}":
            cursor = self.textCursor()
            line_prefix = cursor.block().text()[:cursor.positionInBlock()]
            if not cursor.hasSelection() and not line_prefix.strip():
                remove_count = min(4, len(line_prefix) - len(line_prefix.rstrip(" ")))
                for _ in range(remove_count):
                    cursor.deletePreviousChar()
                self.setTextCursor(cursor)
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
            self._update_language_completions()
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

        if self._language in {"javascript", "css", "c", "cpp", "java", "go", "rust"}:
            position = cursor.positionInBlock()
            prefix = current_line[:position]
            suffix = current_line[position:]
            indentation = re.match(r"^\s*", current_line).group(0)
            opens_block = prefix.rstrip().endswith(("{", "(", "["))
            closes_block = suffix.lstrip().startswith(("}", ")", "]"))
            if opens_block and closes_block:
                cursor.insertText("\n" + indentation + "    \n" + indentation)
                cursor.movePosition(QTextCursor.Up)
                cursor.movePosition(QTextCursor.EndOfLine)
            else:
                extra = "    " if opens_block else ""
                dedent = "    " if not prefix.strip() and suffix.lstrip().startswith("}") else ""
                if dedent and indentation.endswith(dedent):
                    indentation = indentation[:-len(dedent)]
                cursor.insertText("\n" + indentation + extra)
            self.setTextCursor(cursor)
            return

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
        comment_markers = {
            "python": ("#", ""),
            "javascript": ("//", ""),
            "css": ("/*", "*/"),
            "html": ("<!--", "-->"),
            "markdown": ("<!--", "-->"),
            "json": ("//", ""),
            "yaml": ("#", ""),
            "toml": ("#", ""),
            "c": ("//", ""),
            "cpp": ("//", ""),
            "java": ("//", ""),
            "go": ("//", ""),
            "rust": ("//", ""),
        }
        comment_prefix, comment_suffix = comment_markers.get(self._language, ("#", ""))

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

        def is_commented(line: str) -> bool:
            content = line.lstrip()
            return content.startswith(comment_prefix) and (
                not comment_suffix or content.rstrip().endswith(comment_suffix)
            )

        uncomment = bool(non_empty_lines) and all(
            is_commented(line)
            for line in non_empty_lines
        )

        cursor.beginEditBlock()

        for block in blocks:
            line = block.text()

            if not line.strip():
                continue

            line_cursor = QTextCursor(block)
            indent = len(line) - len(line.lstrip())
            content = line[indent:]

            if uncomment:
                content = content[len(comment_prefix):]
                if content.startswith(" "):
                    content = content[1:]
                if comment_suffix:
                    content = content.rstrip()
                    content = content[:-len(comment_suffix)]
                    if content.endswith(" "):
                        content = content[:-1]
            else:
                content = f"{comment_prefix} {content}"
                if comment_suffix:
                    content += f" {comment_suffix}"

            line_cursor.movePosition(QTextCursor.StartOfBlock)
            line_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            line_cursor.insertText(" " * indent + content)

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
