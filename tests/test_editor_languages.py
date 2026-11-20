import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, Qt, QMimeData, QUrl, QPointF
from PySide6.QtGui import QKeyEvent, QTextCursor, QDragEnterEvent, QDropEvent, QImage, QTextDocument
from PySide6.QtCore import QSize
from PySide6.QtTest import QTest
from PySide6.QtNetwork import QTcpServer, QHostAddress
from PySide6.QtWidgets import QApplication

from ui.editor import CodeEditor
from ui.explorer import FileExplorer
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


@pytest.mark.parametrize(
    ("filename", "prefix", "expected", "key"),
    [
        ("site.css", "justi", "justify-content", Qt.Key_Tab),
        ("site.css", "align-i", "align-items", Qt.Key_Return),
        ("main.js", "addEvent", "addEventListener", Qt.Key_Tab),
        ("main.js", "document.getElementByI", "document.getElementById", Qt.Key_Return),
    ],
)
def test_css_and_javascript_completions_accept_with_tab_or_enter(
    qapp, filename, prefix, expected, key
):
    editor = CodeEditor()
    editor.set_file_path(filename)
    editor.setPlainText(prefix)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    editor.resize(500, 300)
    editor.show()
    editor._update_language_completions()
    editor._show_completion()
    qapp.processEvents()

    assert editor._completer.popup().isVisible()
    editor.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier, "\t" if key == Qt.Key_Tab else "\n"))

    assert editor.toPlainText() == expected
    editor.close()


@pytest.mark.parametrize(
    ("typed", "expected", "accept_key"),
    [
        ("addEvent", "addEventListener", Qt.Key_Tab),
        ("addEvent", "addEventListener", Qt.Key_Return),
        ("document.getElementByI", "document.getElementById", Qt.Key_Tab),
        ("document.getElementByI", "document.getElementById", Qt.Key_Return),
    ],
)
def test_javascript_completion_works_during_real_typing(qapp, typed, expected, accept_key):
    editor = CodeEditor()
    editor.set_file_path("main.js")
    editor.resize(500, 300)
    editor.show()
    editor.setFocus()

    QTest.keyClicks(editor, typed)
    qapp.processEvents()

    assert editor.toPlainText() == typed
    assert editor._completer.popup().isVisible()
    expected_completion = expected.split(".")[-1]
    assert editor._completer.currentCompletion() == expected_completion

    QTest.keyClick(editor, accept_key)
    qapp.processEvents()

    assert editor.toPlainText() == expected
    editor.close()


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
        ("section", "<section></section>"),
        ("link:css", '<link rel="stylesheet" href="style.css">'),
        ("input:text", '<input type="text" class="">'),
        ("input:number", '<input type="number" class="">'),
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
    from PySide6.QtCore import QFileInfo
    from pathlib import Path
    from PySide6.QtGui import QIcon
    import ui.main_window as main_window_module
    from ui.file_icons import LauPydeFileIconProvider

    monkeypatch.setattr(main_window_module, "RECENT_PROJECT_FILE", tmp_path / "recent.json")
    window = MainWindow()
    explorer_provider = window.explorer._model.iconProvider()
    tab_provider = window._file_icon_provider
    expected_icons = {
        "index.html": "file-html.svg",
        "site.css": "file-css.svg",
        "app.js": "file-js.svg",
    }
    for name in ("index.html", "site.css", "app.js", "README.md", "Main.java"):
        path = tmp_path / name
        path.write_text("", encoding="utf-8")
        explorer_icon = explorer_provider.icon(QFileInfo(str(path)))
        tab_icon = tab_provider.icon(QFileInfo(str(path)))
        assert not explorer_icon.isNull()
        assert explorer_icon.pixmap(QSize(24, 24)).toImage() == tab_icon.pixmap(QSize(24, 24)).toImage()
        if name in expected_icons:
            asset = Path(__file__).resolve().parents[1] / "assets" / "icons" / expected_icons[name]
            expected_icon = QIcon(str(asset))
            assert explorer_icon.pixmap(QSize(24, 24)).toImage() == expected_icon.pixmap(QSize(24, 24)).toImage()
    assert isinstance(explorer_provider, LauPydeFileIconProvider)
    window.close()


def test_file_tab_close_uses_custom_icon_button(qapp, tmp_path, monkeypatch):
    import ui.main_window as main_window_module

    monkeypatch.setattr(main_window_module, "RECENT_PROJECT_FILE", tmp_path / "recent.json")
    path = tmp_path / "index.html"
    path.write_text("", encoding="utf-8")
    window = MainWindow()
    window.open_file(str(path))

    close_button = window._file_tab_bar.tabButton(0, window._file_tab_bar.ButtonPosition.RightSide)

    assert not window._file_tab_bar.tabsClosable()
    assert close_button is not None
    assert not close_button.icon().isNull()
    window.close()


def test_editor_is_direct_view_and_markdown_preview_uses_toggle(qapp, tmp_path, monkeypatch):
    import ui.main_window as main_window_module

    monkeypatch.setattr(main_window_module, "RECENT_PROJECT_FILE", tmp_path / "recent.json")
    window = MainWindow()

    assert window._editor_content.currentWidget() is window.editor
    assert window._markdown_preview_button.isHidden()
    assert not hasattr(window, "_editor_tabs")

    markdown_path = tmp_path / "README.md"
    markdown_path.write_text("# preview", encoding="utf-8")
    window.open_file(str(markdown_path))
    assert not window._markdown_preview_button.isHidden()

    window._toggle_markdown_preview()
    assert window._editor_content.currentWidget() is window._markdown_preview
    window._toggle_markdown_preview()
    assert window._editor_content.currentWidget() is window.editor
    window.close()


def test_welcome_screen_quick_actions_use_existing_actions(qapp, tmp_path, monkeypatch):
    import ui.main_window as main_window_module
    from PySide6.QtWidgets import QFileDialog, QInputDialog

    monkeypatch.setattr(main_window_module, "RECENT_PROJECT_FILE", tmp_path / "recent.json")
    settings = main_window_module.QSettings(
        main_window_module.SETTINGS_ORGANIZATION, main_window_module.APP_NAME
    )
    previous_recent = settings.value("recent_files", None, type=list)
    settings.setValue("recent_files", [])
    settings.sync()
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("", False))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("", ""))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: "")
    window = MainWindow()
    triggered = {"new": 0, "open": 0, "folder": 0}
    window._new_file_action.triggered.connect(lambda _checked=False: triggered.__setitem__("new", triggered["new"] + 1))
    window._open_file_action.triggered.connect(lambda _checked=False: triggered.__setitem__("open", triggered["open"] + 1))
    window._open_folder_action.triggered.connect(lambda _checked=False: triggered.__setitem__("folder", triggered["folder"] + 1))

    assert window._welcome_footer.text().endswith(f"v{main_window_module.APP_VERSION}")
    assert window._welcome_recent_section.isHidden()
    for action_key in ("new", "open", "folder"):
        window._welcome_action_buttons[action_key].click()

    assert triggered == {"new": 1, "open": 1, "folder": 1}
    window.close()
    if previous_recent is None:
        settings.remove("recent_files")
    else:
        settings.setValue("recent_files", previous_recent)
    settings.sync()


def test_startup_after_closing_project_shows_welcome_screen(qapp, tmp_path, monkeypatch):
    import ui.main_window as main_window_module

    recent_project_file = tmp_path / "recent.json"
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(main_window_module, "RECENT_PROJECT_FILE", recent_project_file)

    first_window = MainWindow()
    first_window.open_folder_path(str(project))
    first_window.close_project()
    first_window.close()

    assert not recent_project_file.exists()

    reopened_window = MainWindow()
    assert reopened_window._editor_stack.currentWidget() is reopened_window._welcome_widget
    assert reopened_window.explorer.isHidden()
    assert reopened_window._bottom_tabs.isHidden()
    reopened_window.open_folder_path(str(project))
    assert not reopened_window.explorer.isHidden()
    assert not reopened_window._bottom_tabs.isHidden()
    reopened_window.close_project()
    assert reopened_window.explorer.isHidden()
    assert reopened_window._bottom_tabs.isHidden()
    reopened_window.close()


def test_welcome_recent_files_are_real_deduplicated_and_reopen_existing_tab(qapp, tmp_path, monkeypatch):
    import ui.main_window as main_window_module
    from PySide6.QtWidgets import QLabel, QToolButton

    monkeypatch.setattr(main_window_module, "RECENT_PROJECT_FILE", tmp_path / "recent.json")
    settings = main_window_module.QSettings(
        main_window_module.SETTINGS_ORGANIZATION, main_window_module.APP_NAME
    )
    previous_recent = settings.value("recent_files", None, type=list)
    files = [tmp_path / f"project_{index}" / f"file_{index}.py" for index in range(6)]
    try:
        settings.setValue("recent_files", [])
        for path in files:
            path.parent.mkdir()
            path.write_text(f"value = {path.stem}\n", encoding="utf-8")

        window = MainWindow()
        for path in files:
            window._record_recent_file(str(path))
        window._record_recent_file(str(files[3]))

        recent = window._recent_file_paths()
        assert recent == [str(files[3]), str(files[5]), str(files[4]), str(files[2]), str(files[1])]
        assert not window._welcome_recent_section.isHidden()
        assert window._welcome_recent_rows.count() == 5
        first_row = window._welcome_recent_rows.itemAt(0).widget()
        recent_button = first_row.findChild(QToolButton, "recentFileButton")
        parent_label = first_row.findChildren(QLabel)[0]
        assert recent_button.text() == files[3].name
        try:
            relative_parent = files[3].parent.relative_to(Path.home())
            expected_parent = "~/" + relative_parent.as_posix()
        except ValueError:
            expected_parent = str(files[3].parent)
        assert parent_label.text() == expected_parent

        window.open_file(str(files[3]))
        window.open_file(str(files[5]))
        assert window._file_tab_bar.count() == 2
        recent_button = None
        for row_index in range(window._welcome_recent_rows.count()):
            row_widget = window._welcome_recent_rows.itemAt(row_index).widget()
            candidate = row_widget.findChild(QToolButton, "recentFileButton")
            if candidate.toolTip() == str(files[3]):
                recent_button = candidate
                break
        assert recent_button is not None
        recent_button.click()
        assert window._current_file_path == str(files[3].resolve())
        assert window._file_tab_bar.count() == 2
        window.close()
    finally:
        if previous_recent is None:
            settings.remove("recent_files")
        else:
            settings.setValue("recent_files", previous_recent)
        settings.sync()


def test_missing_recent_file_is_removed_and_reported(qapp, tmp_path, monkeypatch):
    import ui.main_window as main_window_module
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(main_window_module, "RECENT_PROJECT_FILE", tmp_path / "recent.json")
    settings = main_window_module.QSettings(
        main_window_module.SETTINGS_ORGANIZATION, main_window_module.APP_NAME
    )
    previous_recent = settings.value("recent_files", None, type=list)
    messages = []
    monkeypatch.setattr(QMessageBox, "information", lambda *args: messages.append(args[-1]))
    missing = tmp_path / "removed.py"
    try:
        settings.setValue("recent_files", [str(missing)])
        window = MainWindow()
        window._open_recent_file(str(missing))
        assert messages and "no longer exists" in messages[0]
        assert str(missing) not in settings.value("recent_files", [], type=list)
        window.close()
    finally:
        if previous_recent is None:
            settings.remove("recent_files")
        else:
            settings.setValue("recent_files", previous_recent)
        settings.sync()


def test_markdown_preview_resolves_relative_images_and_styles_document(qapp, tmp_path):
    from PySide6.QtCore import QUrl
    from ui.main_window import MarkdownPreviewBrowser

    image_path = tmp_path / "badge.png"
    image = QImage(12, 12, QImage.Format.Format_ARGB32)
    image.fill(Qt.red)
    assert image.save(str(image_path))

    markdown_path = tmp_path / "README.md"
    preview = MarkdownPreviewBrowser()
    preview.set_markdown_source("# Project\n\n<img src=\"badge.png\" width=\"12\">", str(markdown_path))
    resource = preview.loadResource(QTextDocument.ImageResource, QUrl("badge.png"))
    resolved_image = QImage.fromData(bytes(resource))

    assert not resolved_image.isNull()
    assert "border-bottom" in preview.document().defaultStyleSheet()
    assert "background-color" in preview.document().defaultStyleSheet()
    preview.close()


def test_markdown_preview_loads_remote_svg_asynchronously(qapp):
    from PySide6.QtCore import QUrl
    from ui.main_window import MarkdownPreviewBrowser

    server = QTcpServer()
    assert server.listen(QHostAddress.SpecialAddress.LocalHost, 0)
    svg_data = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="red"/></svg>'
    response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: image/svg+xml\r\n"
        + f"Content-Length: {len(svg_data)}\r\n".encode("ascii")
        + b"Connection: close\r\n\r\n"
        + svg_data
    )

    def respond_to_request():
        socket = server.nextPendingConnection()
        socket.readyRead.connect(
            lambda socket=socket: (
                socket.readAll(),
                socket.write(response),
                socket.disconnectFromHost(),
            )
        )

    server.newConnection.connect(respond_to_request)
    preview = MarkdownPreviewBrowser()
    loaded_urls = []
    preview.image_loaded.connect(loaded_urls.append)
    image_url = QUrl(f"http://127.0.0.1:{server.serverPort()}/icon.svg")

    assert preview.loadResource(QTextDocument.ImageResource, image_url).isNull()
    QTest.qWait(300)

    assert image_url.toString() in loaded_urls
    cached = preview.loadResource(QTextDocument.ImageResource, image_url)
    assert isinstance(cached, QImage)
    assert not cached.isNull()
    preview.close()
    server.close()


def test_key_shortcuts_visibility_is_restored_from_settings(qapp, tmp_path, monkeypatch):
    import ui.main_window as main_window_module

    monkeypatch.setattr(main_window_module, "RECENT_PROJECT_FILE", tmp_path / "recent.json")
    settings = main_window_module.QSettings(
        main_window_module.SETTINGS_ORGANIZATION, main_window_module.APP_NAME
    )
    previous_value = settings.value("show_key_shortcuts", None)
    try:
        settings.setValue("show_key_shortcuts", False)
        settings.sync()
        first_window = MainWindow()
        assert first_window.explorer._commands_section.isHidden()
        assert not first_window._show_commands_list_action.isChecked()
        first_window.close()

        second_window = MainWindow()
        assert second_window.explorer._commands_section.isHidden()
        assert not second_window._show_commands_list_action.isChecked()

        second_window._show_commands_list_action.trigger()
        assert not second_window.explorer._commands_section.isHidden()
        assert second_window._show_commands_list_action.isChecked()
        assert settings.value("show_key_shortcuts", False, type=bool)

        second_window.explorer._commands_toggle.click()
        assert second_window.explorer._commands_section.isHidden()
        assert not second_window._show_commands_list_action.isChecked()
        assert not settings.value("show_key_shortcuts", True, type=bool)
        second_window.close()
    finally:
        if previous_value is None:
            settings.remove("show_key_shortcuts")
        else:
            settings.setValue("show_key_shortcuts", previous_value)
        settings.sync()


def test_javascript_enter_indents_after_opening_brace(qapp):
    editor = CodeEditor()
    editor.set_file_path("main.js")
    editor.setPlainText("button.addEventListener('click', function() {")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)

    editor.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier, "\n"))

    assert editor.toPlainText().endswith("{\n    ")


def test_javascript_enter_splits_auto_paired_dom_callback_braces(qapp):
    editor = CodeEditor()
    editor.set_file_path("main.js")
    editor.setPlainText("button.addEventListener('click', function() {})")
    cursor = editor.textCursor()
    cursor.setPosition(editor.toPlainText().index("}") )
    editor.setTextCursor(cursor)

    editor.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier, "\n"))

    assert editor.toPlainText() == "button.addEventListener('click', function() {\n    \n})"
    assert editor.textCursor().block().text() == "    "


def test_javascript_closing_brace_dedents(qapp):
    editor = CodeEditor()
    editor.set_file_path("main.js")
    editor.setPlainText("if (ready) {\n    ")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)

    editor.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_BraceRight, Qt.NoModifier, "}"))

    assert editor.toPlainText() == "if (ready) {\n}"


def test_tabs_show_absolute_path_for_files_outside_active_folder(qapp, tmp_path, monkeypatch):
    import ui.main_window as main_window_module

    monkeypatch.setattr(main_window_module, "RECENT_PROJECT_FILE", tmp_path / "recent.json")
    project = tmp_path / "project"
    external = tmp_path / "shared" / "Main.java"
    project.mkdir()
    external.parent.mkdir()
    external.write_text("class Main {}", encoding="utf-8")
    window = MainWindow()
    window.open_file(str(external))
    assert window._file_tab_bar.tabText(0) == "Main.java"
    window._current_folder = str(project)
    window._refresh_file_tab_labels()

    assert window._file_tab_bar.tabText(0) == str(external.resolve())
    window.close()


def test_dropping_folder_on_editor_opens_workspace(qapp, tmp_path, monkeypatch):
    import ui.main_window as main_window_module

    monkeypatch.setattr(main_window_module, "RECENT_PROJECT_FILE", tmp_path / "recent.json")
    folder = tmp_path / "dropped-project"
    folder.mkdir()
    window = MainWindow()
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(folder))])
    enter_event = QDragEnterEvent(
        QPointF(10, 10), Qt.CopyAction, mime_data, Qt.LeftButton, Qt.NoModifier
    )
    drop_event = QDropEvent(
        QPointF(10, 10), Qt.CopyAction, mime_data, Qt.LeftButton, Qt.NoModifier
    )

    qapp.sendEvent(window.editor, enter_event)
    qapp.sendEvent(window.editor, drop_event)

    assert enter_event.isAccepted()
    assert drop_event.isAccepted()
    assert window._current_folder == str(folder.resolve())
    assert window.explorer._project_root == str(folder.resolve())
    assert window.terminal_panel._working_dir == str(folder.resolve())
    assert main_window_module.RECENT_PROJECT_FILE.exists()
    window.close()


def test_explorer_root_is_selected_nested_workspace(qapp, tmp_path):
    project = tmp_path / "30days_python_challenge"
    selected_folder = project / "day_three"
    selected_folder.mkdir(parents=True)
    (selected_folder / "main.py").write_text("print(3)", encoding="utf-8")
    (project / "day_four").mkdir()

    explorer = FileExplorer()
    explorer.set_root_folder(str(selected_folder))
    QTest.qWait(250)

    root_index = explorer._tree.rootIndex()
    assert Path(explorer._model.filePath(root_index)).resolve() == project.resolve()
    selected_index = explorer._model.index(str(selected_folder))
    sibling_index = explorer._model.index(str(project / "day_four"))
    assert selected_index.isValid()
    assert not explorer._tree.isRowHidden(selected_index.row(), root_index)
    assert explorer._tree.isRowHidden(sibling_index.row(), root_index)

    visible_names = [
        explorer._model.fileName(explorer._model.index(row, 0, selected_index))
        for row in range(explorer._model.rowCount(selected_index))
    ]
    assert "main.py" in visible_names


def test_key_shortcuts_section_stays_content_sized(qapp):
    explorer = FileExplorer()
    explorer.resize(220, 900)
    explorer.populate_commands(MainWindow())
    explorer.show()
    qapp.processEvents()

    section = explorer._commands_section
    assert section.sizePolicy().verticalPolicy().name == "Fixed"
    assert section.height() <= section.sizeHint().height() + 2
    assert explorer._tree.height() > section.height()
    explorer.close()


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