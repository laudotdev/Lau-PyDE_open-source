import json

import pytest

from core.update_checker import (
    ReleaseInfo,
    UpdateCheckError,
    compare_versions,
    parse_release,
    select_download_url,
    DOWNLOADS_PAGE,
)


@pytest.mark.parametrize("installed, latest", [("1.1.0", "1.1.0"), ("1.2.0", "1.1.9"), ("1.10.0", "1.9.0")])
def test_equal_or_older_release_is_not_newer(installed, latest):
    assert compare_versions(latest, installed) <= 0


@pytest.mark.parametrize("latest", ["1.1.1", "1.2.0", "2.0.0", "v2.0.0"])
def test_newer_release_is_detected(latest):
    assert compare_versions(latest, "1.1.0") > 0


def test_development_version_1_1_0_is_newer_than_published_1_0_0():
    assert compare_versions("1.1.0", "1.0.0") > 0


def test_invalid_versions_are_safe():
    assert compare_versions("not-a-version", "1.0.0") is None
    assert compare_versions(None, "1.0.0") is None


@pytest.mark.parametrize("tag, version", [
    ("Lau-PyDE_v1.0", "1.0.0"),
    ("Lau-PyDE_v1.0.0", "1.0.0"),
    ("v1.0", "1.0.0"),
    ("v1.0.0", "1.0.0"),
    ("1.0", "1.0.0"),
    ("1.0.0", "1.0.0"),
])
def test_known_release_tag_formats_are_normalized(tag, version):
    release = parse_release({
        "tag_name": tag,
        "html_url": "https://github.com/laudotdev/Lau-PyDE_open-source/releases/tag/" + tag,
        "assets": [],
    })
    assert release.version == version


def test_release_metadata_and_assets_are_parsed():
    release = parse_release({
        "tag_name": "v1.2.0",
        "name": "Lau-PyDE 1.2.0",
        "body": "Bug fixes",
        "html_url": "https://github.com/laudotdev/Lau-PyDE_open-source/releases/tag/v1.2.0",
        "draft": False,
        "prerelease": False,
        "assets": [{"name": "Lau-PyDE.exe", "browser_download_url": "https://example/exe"}],
    })
    assert release == ReleaseInfo("1.2.0", "Lau-PyDE 1.2.0", "Bug fixes", "https://github.com/laudotdev/Lau-PyDE_open-source/releases/tag/v1.2.0", (("Lau-PyDE.exe", "https://example/exe"),))


def test_draft_prerelease_and_missing_metadata_are_rejected():
    for flags in ({"draft": True}, {"prerelease": True}, {"tag_name": ""}):
        payload = {"tag_name": "v1.2.0", "html_url": "https://example", "assets": [], **flags}
        with pytest.raises(UpdateCheckError):
            parse_release(payload)


def test_platform_asset_selection_falls_back_to_release_page():
    release = ReleaseInfo("1.2.0", "", "", "https://example/release", (("app.pkg.tar.zst", "https://example/pkg"),))
    assert select_download_url(release, "arch") == "https://example/pkg"
    assert select_download_url(release, "windows") == DOWNLOADS_PAGE
    assert select_download_url(release, "linux") == DOWNLOADS_PAGE

