from types import SimpleNamespace as NS

import numpy as np
import pytest

from mtah.io.external import IDSSE_MATCHES, _labels_from_frames, load_idsse

HOME, AWAY = NS(name="home"), NS(name="away")


def frame(state, owner):
    return NS(ball_state=NS(value=state), ball_owning_team=owner)


def test_label_mapping():
    frames = [frame("alive", HOME), frame("alive", AWAY), frame("dead", HOME),
              frame("alive", None), frame("alive", HOME)]
    assert "".join(_labels_from_frames(frames, HOME)) == "HADAH"


def test_owner_missing_carries_last_alive_owner():
    frames = [frame("alive", AWAY), frame("alive", None), frame("alive", None)]
    assert "".join(_labels_from_frames(frames, HOME)) == "AAA"


def test_match_list():
    assert len(IDSSE_MATCHES) == 7


@pytest.mark.network
def test_load_one(tmp_path):
    track, labels = load_idsse(IDSSE_MATCHES[0])
    track.validate()
    assert set(np.unique(labels)) <= {"H", "A", "D"}
    alive = labels != "D"
    assert 0.3 < (labels[alive] == "H").mean() < 0.7  # home share of in-play frames
    assert (labels == "D").mean() > 0.05
    assert len(track.periods) == 2


def test_owner_resets_at_period_boundary():
    p1, p2 = NS(id=1), NS(id=2)
    frames = [NS(ball_state=NS(value="alive"), ball_owning_team=AWAY, period=p1),
              NS(ball_state=NS(value="alive"), ball_owning_team=None, period=p2)]
    assert "".join(_labels_from_frames(frames, HOME)) == "AD"


def test_cache_path_is_versioned(tmp_path):
    from mtah.io.external import CACHE_VERSION, _cache_path

    assert f"v{CACHE_VERSION}" in _cache_path("J03WMX", tmp_path).name


def _fake_curl(content: bytes):
    """Stand-in for subprocess.run: writes `content` to the -o target and records the call."""
    calls = []

    def run(cmd, check):
        calls.append(cmd)
        out = cmd[cmd.index("-o") + 1]
        with open(out, "wb") as handle:
            handle.write(content)

    return run, calls


def test_fetch_verifies_checksum_and_uses_fail(tmp_path, monkeypatch):
    import hashlib

    from mtah.io import external

    payload = b"<xml/>"
    monkeypatch.setattr(external, "_url", lambda m, k: f"https://x/{m}_{k}.xml")
    monkeypatch.setattr(external, "_manifest",
                        lambda: {f"J03WMX_{k}.xml": hashlib.sha256(payload).hexdigest()
                                 for k in ("meta", "tracking")})
    run, calls = _fake_curl(payload)
    monkeypatch.setattr(external.subprocess, "run", run)
    meta, tracking = external.fetch_idsse("J03WMX", tmp_path)
    assert meta.read_bytes() == payload and tracking.exists()
    assert all("--fail" in cmd for cmd in calls)
    assert not list(tmp_path.glob("*.part"))


def test_fetch_rejects_a_corrupt_download(tmp_path, monkeypatch):
    from mtah.io import external

    monkeypatch.setattr(external, "_url", lambda m, k: f"https://x/{m}_{k}.xml")
    monkeypatch.setattr(external, "_manifest", lambda: {"J03WMX_meta.xml": "0" * 64})
    run, _ = _fake_curl(b"<html>error page</html>")
    monkeypatch.setattr(external.subprocess, "run", run)
    with pytest.raises(ValueError, match="checksum"):
        external.fetch_idsse("J03WMX", tmp_path)
    assert not (tmp_path / "J03WMX_meta.xml").exists()


def test_manifest_covers_every_idsse_file():
    from mtah.io.external import _manifest

    manifest = _manifest()
    assert len(manifest) == 2 * len(IDSSE_MATCHES)
    assert all(any(m in name for name in manifest) for m in IDSSE_MATCHES)
