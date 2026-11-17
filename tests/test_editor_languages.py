import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ui.editor import CodeEditor
from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_javascript_uses_language_completions_and_structural_diagnostics(qapp):
    editor = CodeEditor()
    editor.set_file_path("sample.js")
    editor.setPlainText("function greet() { return 'hello'; }")

    assert editor.get_error_messages() == []
    assert "function" in editor._completion_model.stringList()
    assert "greet" in editor._completion_model.stringList()

    editor.setPlainText("function greet() {")
    assert editor.get_error_messages() == ["Line 1: '}' is missing."]


def test_html_reports_unclosed_tags(qapp):
    editor = CodeEditor()
    editor.set_file_path("index.html")
    editor.setPlainText("<main>\n  <section>\n</main>")

    assert any("Unexpected closing </main>" in message for message in editor.get_error_messages())


def test_html_boilerplate_and_tag_completion_keys(qapp):
    editor = CodeEditor()
    editor.set_file_path("index.html")
    editor.setPlainText("<h1")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    editor.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier, "\t"))
    assert editor.toPlainText() == "<h1></h1>"
    assert editor.textCursor().position() == 4

    editor.setPlainText("!")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    editor.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier, "\n"))
    assert editor.toPlainText().startswith("<!DOCTYPE html>")
    assert editor.textCursor().block().text() == ""

    editor.setPlainText("<h2")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    editor.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Greater, Qt.NoModifier, ">"))
    assert editor.toPlainText() == "<h2></h2>"
    assert editor.textCursor().position() == 4


@pytest.mark.parametrize(
    ("abbreviation", "expected"),
    [
        ("h1", "<h1></h1>"),
        ("link:css", '<link rel="stylesheet" href="style.css">'),
        ("input:text", '<input type="text" class="">'),
    ],
)
def test_html_abbreviations_expand_on_tab(qapp, abbreviation, expected):
    editor = CodeEditor()
    editor.set_file_path("index.html")
    editor.setPlainText(abbreviation)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)

    editor.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier, "\t"))

    assert editor.toPlainText() == expected


def test_css_and_javascript_use_distinct_keyword_colors(qapp):
    editor = CodeEditor()
    colors = {}
    for extension, language in ((".py", "python"), (".css", "css"), (".js", "javascript")):
        editor.set_file_path("sample" + extension)
        if language == "python":
            color = editor._highlighter._rules[0][1].foreground().color().name()
        else:
            color = editor._highlighter._rules[0][1].foreground().color().name()
        colors[language] = color

    assert len(set(colors.values())) == 3


def test_file_icons_use_custom_language_artwork(qapp, tmp_path, monkeypatch):
    import ui.main_window as main_window_module

    monkeypatch.setattr(main_window_module, "RECENT_PROJECT_FILE", tmp_path / "recent.json")
    window = MainWindow()
    for name in ("index.html", "site.css", "app.js", "README.md"):
        assert not window._file_icon(name).isNull()
    window.close()


def test_debounced_autosave_writes_active_file(qapp, tmp_path, monkeypatch):
    import ui.main_window as main_window_module

    monkeypatch.setattr(main_window_module, "RECENT_PROJECT_FILE", tmp_path / "recent.json")
    path = tmp_path / "index.html"
    path.write_text("<h1>start</h1>", encoding="utf-8")
    window = MainWindow()
    window.open_file(str(path))
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.Document)
    cursor.insertText("<h1>autosaved</h1>")
    window.editor.setTextCursor(cursor)

    QTest.qWait(400)

    assert path.read_text(encoding="utf-8") == "<h1>autosaved</h1>"
    assert not window.editor.document().isModified()
    window.close()


def test_markdown_reports_unclosed_code_fence(qapp):
    editor = CodeEditor()
    editor.set_file_path("README.md")
    editor.setPlainText("```python\nprint('hello')\n")

    assert editor.get_error_messages() == ["Unclosed Markdown code fence."]


def test_python_diagnostics_remain_enabled_after_language_switch(qapp):
    editor = CodeEditor()
    editor.set_file_path("sample.js")
    editor.setPlainText("const answer = 42;")
    assert editor.get_error_messages() == []

    editor.set_file_path("sample.py")
    editor.setPlainText("def broken(:")
    assert editor.get_error_messages()


def test_file_tabs_save_and_restore_when_switching(qapp, tmp_path, monkeypatch):
    import ui.main_window as main_window_module

    monkeypatch.setattr(main_window_module, "RECENT_PROJECT_FILE", tmp_path / "recent.json")
    first = tmp_path / "index.html"
    second = tmp_path / "site.css"
    first.write_text("<h1>start</h1>", encoding="utf-8")
    second.write_text("body {}", encoding="utf-8")

    window = MainWindow()
    window._current_folder = None
    window.open_file(str(first))
    assert not window._file_tab_bar.isHidden()
    assert window._file_tab_bar.tabText(0) == "index.html"
    assert window._file_tab_bar.tabToolTip(0) == str(first)

    cursor = window.editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    cursor.insertText(" changed")
    window.editor.setTextCursor(cursor)
    window.open_file(str(second))

    assert first.read_text(encoding="utf-8") == "<h1>start</h1> changed"
    window._file_tab_bar.setCurrentIndex(0)
    assert window.editor.toPlainText() == "<h1>start</h1> changed"
    window.close()