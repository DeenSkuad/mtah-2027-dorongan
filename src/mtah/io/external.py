"""IDSSE / DFL Bundesliga open data (Bassek et al. 2025, CC-BY) -> MatchTracking + H/A/D labels.

These 7 matches carry per-frame BallPossession and BallStatus, i.e. exactly our label set, which is
what makes them the internal validation set (rule R3: never tune on the public 5 minutes).
Files are fetched once into a cache outside the repository (default ~/.cache/mtah/idsse).
"""

import subprocess
from pathlib import Path

import numpy as np

from mtah.schema import MatchTracking

IDSSE_MATCHES = ("J03WMX", "J03WN1", "J03WOH", "J03WOY", "J03WPY", "J03WQQ", "J03WR9")
DEFAULT_CACHE = Path.home() / ".cache" / "mtah" / "idsse"
CACHE_VERSION = 2  # bump whenever parsing or label semantics change
METRICA_IDS = ("metrica1", "metrica2")  # Metrica Sports sample games 1-2, see mtah.io.metrica
EXTERNAL_MATCHES = IDSSE_MATCHES + METRICA_IDS  # the full bench: 2 providers, 9 matches


def _cache_path(match_id: str, cache_dir: Path) -> Path:
    return cache_dir / f"{match_id}.v{CACHE_VERSION}.npz"


def _url(match_id: str, kind: str) -> str:
    from kloppy._providers.sportec import get_IDSSE_url

    return get_IDSSE_url(match_id, kind)


def _manifest() -> dict[str, str]:
    """{file name: SHA-256} of the 14 IDSSE XMLs we trained on (config/idsse_sha256.txt). The
    files come from a mirror that tracks a moving branch, so a download is only accepted if it
    is byte-identical to ours (R5)."""
    from mtah.constants import REPO_ROOT

    lines = (REPO_ROOT / "config" / "idsse_sha256.txt").read_text().splitlines()
    return {name: digest for digest, name in (line.split() for line in lines if line.strip())}


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_idsse(match_id: str, cache_dir: Path = DEFAULT_CACHE) -> tuple[Path, Path]:
    """Download (resumably) the meta and tracking XML for one match; return their paths.
    A download goes to a .part file and only becomes the cached file once its checksum matches
    the manifest, so an HTTP error page or a truncated file is never cached."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest = _manifest()
    paths = []
    for kind in ("meta", "tracking"):
        url = _url(match_id, kind)
        path = cache_dir / url.rsplit("/", 1)[-1]
        if not path.exists():
            part = path.with_name(path.name + ".part")
            subprocess.run(["curl", "-sSL", "--fail", "-C", "-", "--retry", "5", "-o", str(part),
                            url], check=True)
            if _sha256(part) != manifest.get(path.name):
                part.unlink()
                raise ValueError(f"checksum mismatch for {path.name}: the mirror changed or the "
                                 "download is corrupt; see config/idsse_sha256.txt")
            part.replace(path)
        paths.append(path)
    return paths[0], paths[1]


def _labels_from_frames(frames, home_team) -> np.ndarray:
    """D when the ball is dead; else the owning team. A missing owner keeps the last owner
    within the same period; nothing carries across a period boundary."""
    labels = np.empty(len(frames), dtype="<U1")
    last_owner = "D"
    period = None
    for index, frame in enumerate(frames):
        frame_period = getattr(getattr(frame, "period", None), "id", None)
        if frame_period != period:
            period, last_owner = frame_period, "D"
        if frame.ball_state is None or frame.ball_state.value != "alive":
            labels[index] = "D"
            continue
        owner = frame.ball_owning_team
        if owner is not None:
            last_owner = "H" if owner is home_team else "A"
        labels[index] = last_owner
    return labels


def _to_track(dataset, default_pitch: tuple[float, float] = (105.0, 68.0)) -> MatchTracking:
    """kloppy dataset (normalised 'kloppy' coordinates) -> MatchTracking in metres. Providers
    that publish no pitch size (Metrica) get default_pitch."""
    dims = dataset.metadata.pitch_dimensions
    length = float(dims.pitch_length or default_pitch[0])
    width = float(dims.pitch_width or default_pitch[1])
    home, away = dataset.metadata.teams[0], dataset.metadata.teams[1]
    roster = [p for p in home.players] + [p for p in away.players]
    slot_of = {p.player_id: i for i, p in enumerate(roster)}
    team_of_slot = np.array([0] * len(home.players) + [1] * len(away.players), dtype=np.int8)

    frames = dataset.frames
    T, N = len(frames), len(roster)
    players = np.full((T, N, 2), np.nan, dtype=np.float32)
    ball = np.full((T, 2), np.nan, dtype=np.float32)
    period_ids = np.empty(T, dtype=np.int16)
    for t, frame in enumerate(frames):
        period_ids[t] = frame.period.id
        if frame.ball_coordinates is not None:
            ball[t] = (frame.ball_coordinates.x * length, frame.ball_coordinates.y * width)
        for player, data in frame.players_data.items():
            if data.coordinates is not None and player.player_id in slot_of:
                players[t, slot_of[player.player_id]] = (data.coordinates.x * length,
                                                         data.coordinates.y * width)

    edges = np.flatnonzero(np.diff(period_ids)) + 1
    bounds = np.concatenate(([0], edges, [T]))
    periods = tuple((int(a), int(b)) for a, b in zip(bounds[:-1], bounds[1:], strict=True))
    return MatchTracking(players, team_of_slot, ball, periods, (length, width),
                         int(round(dataset.metadata.frame_rate)))


def _load_cached(cached: Path) -> tuple[MatchTracking, np.ndarray]:
    z = np.load(cached)
    periods = tuple(map(tuple, z["periods"].tolist()))
    track = MatchTracking(z["players"], z["team_of_slot"], z["ball"], periods,
                          tuple(z["pitch"].tolist()), int(z["fps"]))
    return track, z["labels"]


def _save_cached(cached: Path, track: MatchTracking, labels: np.ndarray) -> None:
    np.savez_compressed(cached, players=track.players, team_of_slot=track.team_of_slot,
                        ball=track.ball, periods=np.array(track.periods),
                        pitch=np.array(track.pitch), fps=track.fps, labels=labels)


def load_idsse(match_id: str, cache_dir: Path = DEFAULT_CACHE) -> tuple[MatchTracking, np.ndarray]:
    """One IDSSE match as (MatchTracking, labels). Parsed once, then served from an .npz cache."""
    cached = _cache_path(match_id, cache_dir)
    if cached.exists():
        return _load_cached(cached)

    from kloppy import sportec

    meta, raw = fetch_idsse(match_id, cache_dir)
    dataset = sportec.load_tracking(meta_data=str(meta), raw_data=str(raw),
                                    coordinates="kloppy", only_alive=False)
    track = _to_track(dataset)
    labels = _labels_from_frames(dataset.frames, dataset.metadata.teams[0])
    track.validate()
    _save_cached(cached, track, labels)
    return track, labels


def load_external(match_id: str) -> tuple[MatchTracking, np.ndarray]:
    """Any bench match by id: IDSSE codes or metrica1/metrica2."""
    from mtah.io import metrica

    if match_id in metrica.METRICA_MATCHES:
        return metrica.load_metrica(match_id)
    return load_idsse(match_id)
