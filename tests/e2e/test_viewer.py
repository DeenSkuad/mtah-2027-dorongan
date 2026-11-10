"""End-to-end tests of viewer/possession_viewer.html in the installed Chrome (Playwright).

Synthetic tracking only, never the match (R1). Run: pytest -m e2e tests/e2e
"""

import functools
import http.server
import json
import shutil
import subprocess
import threading

import numpy as np
import pytest

from mtah.constants import REPO_ROOT
from mtah.schema import MatchTracking
from mtah.viewer import viewer_payload

pytestmark = pytest.mark.e2e
FPS = 25


def _export(seconds: int) -> dict:
    """Two halves; possession alternates H/D/A in 20 s blocks; 22 jogging players + ball."""
    T = seconds * FPS
    rng = np.random.default_rng(0)
    base = rng.uniform((10, 5), (95, 63), size=(1, 22, 2))
    players = (base + np.cumsum(rng.normal(0, 0.05, (T, 22, 2)), axis=0)).astype(np.float32)
    ball = players[:, 0] + np.float32(0.5)
    blocks = np.array(list("HDA"))[(np.arange(T) // (20 * FPS)) % 3]
    track = MatchTracking(players, np.array([0] * 11 + [1] * 11, np.int8), ball,
                          ((0, T // 2), (T // 2, T)), (105.0, 68.0), FPS)
    return viewer_payload(track, blocks, home="BLUE", away="ORANGE", truth=blocks,
                          source="synthetic e2e")


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    root = tmp_path_factory.mktemp("viewer")
    shutil.copy(REPO_ROOT / "viewer" / "possession_viewer.html", root)
    (root / "long.json").write_text(json.dumps(_export(600)))
    (root / "short.json").write_text(json.dumps(_export(6)))
    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc=duration=6:size=320x180:rate=25", "-c:v", "libvpx-vp9",
                        str(root / "clip.webm")], check=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield root, f"http://127.0.0.1:{server.server_port}/possession_viewer.html"
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        yield b
        b.close()


@pytest.fixture
def page(browser, site):
    _, url = site
    pg = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(f"{url}?data=long.json")
    pg.wait_for_function("window.possessionLab && window.possessionLab.state().loaded")
    yield pg
    assert errors == [], errors
    pg.close()


def test_loads_file_and_names_teams(page):
    assert page.locator(".home-name").first.inner_text() == "BLUE"
    assert "synthetic e2e" in page.locator("#source").inner_text()
    assert page.locator("#empty").is_hidden()
    assert page.locator("#clock").inner_text().endswith("10:00")


def test_possession_share_after_seek(page):
    page.evaluate("possessionLab.seek(3 * 60 * 25)")  # 3 full H/D/A cycles: equal shares
    assert page.locator("#poss-home").inner_text() == "50%"
    assert page.locator("#poss-away").inner_text() == "50%"
    assert "100%" in page.locator("#agree").inner_text()  # model == reference here


def test_spell_click_seeks_to_its_start(page):
    third = page.locator(".spell").nth(2)
    start = int(third.get_attribute("data-f"))
    third.click()
    assert page.evaluate("possessionLab.state().frame") == start
    assert "now" in third.get_attribute("class")


def test_stoppage_filter_lists_only_dead_spells(page):
    page.locator(".chip[data-f='D']").click()
    names = page.locator(".spell span:nth-child(2)").all_inner_texts()
    assert names and set(names) == {"Stoppage"}
    assert page.locator("#spell-count").inner_text() == f"· {len(names)}"


def test_space_toggles_playback(page):
    page.keyboard.press("Space")
    assert page.evaluate("possessionLab.state().playing")
    page.keyboard.press("Space")
    assert not page.evaluate("possessionLab.state().playing")


def test_timeline_click_seeks_proportionally(page):
    box = page.locator("#tl-pred").bounding_box()
    page.mouse.click(box["x"] + box["width"] * 0.5, box["y"] + box["height"] / 2)
    frame = page.evaluate("possessionLab.state().frame")
    assert abs(frame - 600 * FPS / 2) < 600 * FPS * 0.01


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg for the test clip")
def test_mismatched_video_warns_and_matching_video_does_not(page, site):
    root, url = site
    page.set_input_files("#video-file", str(root / "clip.webm"))   # 6 s clip vs 10 min file
    page.wait_for_selector("#warn:not([hidden])")
    assert "don't match" in page.locator("#warn").inner_text()
    assert page.locator("#map-card").is_visible()                   # pitch moves to the rail

    page.goto(f"{url}?data=short.json")                              # 6 s file vs 6 s clip
    page.wait_for_function("window.possessionLab.state().loaded")
    page.set_input_files("#video-file", str(root / "clip.webm"))
    page.wait_for_function("document.querySelector('video').readyState >= 1")
    assert page.evaluate("possessionLab.checkDuration()") is True
    assert page.locator("#warn").is_hidden()
