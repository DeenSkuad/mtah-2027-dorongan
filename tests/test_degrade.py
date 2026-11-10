import numpy as np

from mtah.degrade import DegradeConfig, degrade, load_config
from mtah.schema import MatchTracking


def synthetic(T=30_000, N=6, seed=1):
    rng = np.random.default_rng(seed)
    players = rng.uniform(0, 60, (T, N, 2)).astype(np.float32)
    ball = rng.uniform(0, 60, (T, 2)).astype(np.float32)
    ball[100:300] = np.nan  # pre-existing gap
    return MatchTracking(players, np.array([0, 0, 0, 1, 1, 1], np.int8), ball,
                         ((0, T // 2), (T // 2, T)), (105.0, 68.0))


def test_missing_fraction():
    out = degrade(synthetic(), DegradeConfig(ball_missing_frac=0.41), np.random.default_rng(0))
    assert abs(np.isnan(out.ball[:, 0]).mean() - 0.41) <= 0.02


def test_never_unhides():
    track = synthetic()
    out = degrade(track, DegradeConfig(), np.random.default_rng(0))
    assert np.isnan(out.ball[100:300]).all()


def test_deterministic():
    a = degrade(synthetic(), DegradeConfig(), np.random.default_rng(7))
    b = degrade(synthetic(), DegradeConfig(), np.random.default_rng(7))
    np.testing.assert_array_equal(a.ball, b.ball)
    np.testing.assert_array_equal(a.players, b.players)


def test_team_preserved():
    track = synthetic()
    out = degrade(track, DegradeConfig(id_switch_per_min=20.0), np.random.default_rng(0))
    for team in (0, 1):
        cols = track.team_of_slot == team
        before = np.sort(track.players[:, cols, 0], axis=1)
        after = np.sort(out.players[:, cols, 0], axis=1)
        np.testing.assert_array_equal(before, after)
    assert not np.array_equal(track.players, out.players)


def test_input_not_mutated():
    track = synthetic()
    ball = track.ball.copy()
    degrade(track, DegradeConfig(), np.random.default_rng(0))
    np.testing.assert_array_equal(track.ball, ball)


def test_load_default_config():
    assert load_config().ball_missing_frac == 0.41


def test_full_blackout_terminates():
    cfg = DegradeConfig(ball_missing_frac=1.0)
    out = degrade(synthetic(T=2_000), cfg, np.random.default_rng(0))
    assert np.isnan(out.ball).all()


def test_in_play_mask_drops_empty_frames():
    from mtah.degrade import in_play_mask

    track = synthetic(T=100)
    players = track.players.copy()
    players[:30] = np.nan
    mask = in_play_mask(players, min_players=4)
    assert not mask[:30].any() and mask[30:].all()


def _hash(track):
    import hashlib

    return hashlib.sha256(track.ball.tobytes() + track.players.tobytes()).hexdigest()[:16]


def test_defaults_unchanged():
    """Frozen before the edge/slow/off-pitch/player knobs existed: defaults must not move."""
    out = degrade(synthetic(), DegradeConfig(), np.random.default_rng(0))
    assert _hash(out) == "a9df24d3593eb0bc"


def test_offpitch_hidden():
    track = synthetic()
    ball = track.ball.copy()
    ball[1000:1100] = (-5.0, 30.0)
    track = MatchTracking(track.players, track.team_of_slot, ball, track.periods, track.pitch)
    out = degrade(track, DegradeConfig(ball_missing_frac=0.0, offpitch_visible=False),
                  np.random.default_rng(0))
    assert np.isnan(out.ball[1000:1100]).all()
    assert np.isfinite(out.ball[1100:1200]).all()


def test_edge_boost_concentrates_gaps():
    from mtah.degrade import near_edge

    track = synthetic()
    edge = near_edge(track.ball, track.pitch)
    cfg = DegradeConfig(ball_missing_frac=0.3, gap_len_median_frames=1, gap_len_sigma=0.01,
                        edge_boost=8.0, id_switch_per_min=0)
    out = degrade(track, cfg, np.random.default_rng(0))
    hidden = np.isnan(out.ball[:, 0]) & ~np.isnan(track.ball[:, 0])
    assert hidden[edge].mean() > 2 * hidden[~edge & np.isfinite(track.ball[:, 0])].mean()


def test_player_missing_frac_reached():
    track = synthetic()
    out = degrade(track, DegradeConfig(player_missing_frac=0.15, id_switch_per_min=0),
                  np.random.default_rng(0))
    assert abs(np.isnan(out.players[:, :, 0]).mean() - 0.15) <= 0.02


def test_referee_slot_untouched():
    track = synthetic()
    ref = np.full((track.n_frames(), 1, 2), 50.0, dtype=np.float32)
    track = MatchTracking(np.concatenate([track.players, ref], axis=1),
                          np.append(track.team_of_slot, -1).astype(np.int8), track.ball,
                          track.periods, track.pitch)
    out = degrade(track, DegradeConfig(player_missing_frac=0.3), np.random.default_rng(0))
    np.testing.assert_array_equal(out.players[:, -1], ref[:, 0])
    out.validate()


def test_no_visible_ball_ok():
    track = synthetic()
    track = MatchTracking(track.players, track.team_of_slot,
                          np.full_like(track.ball, np.nan), track.periods, track.pitch)
    cfg = DegradeConfig(edge_boost=4, slow_boost=4, offpitch_visible=False)
    out = degrade(track, cfg, np.random.default_rng(0))
    assert np.isnan(out.ball).all()


def test_scenario_unknown_raises():
    import pytest

    from mtah.degrade import SCENARIOS, scenario

    assert scenario(DegradeConfig(), "all").edge_boost == SCENARIOS["edge"]["edge_boost"]
    with pytest.raises(KeyError):
        scenario(DegradeConfig(), "edgy")


def _gappy(edge_only: bool, T=40_000, seed=3):
    """Ball visible except 1-frame gaps that start either only near the edge or anywhere."""
    from mtah.degrade import near_edge

    track = synthetic(T=T, seed=seed)
    ball = track.ball.copy()
    ball[100:300] = ball[99]  # remove the pre-existing gap
    rng = np.random.default_rng(seed)
    edge = near_edge(ball, track.pitch)
    pool = np.flatnonzero(edge[:-1]) if edge_only else np.arange(T - 1)
    starts = rng.choice(pool, size=400, replace=False) + 1
    ball[starts] = np.nan
    return MatchTracking(track.players, track.team_of_slot, ball, track.periods, track.pitch)


def _full_pitch(track, n_players=22):
    """Pad to n_players team slots so in_play_mask (>=18 tracked) holds."""
    T = track.n_frames()
    extra = n_players - track.players.shape[1]
    players = np.concatenate([track.players, np.full((T, extra, 2), 30.0, np.float32)], axis=1)
    team = np.array([0] * (n_players // 2) + [1] * (n_players // 2), np.int8)
    return MatchTracking(players, team, track.ball, track.periods, track.pitch)


def test_measure_edge_boost():
    from mtah.degrade import measure_knobs

    assert measure_knobs(_full_pitch(_gappy(edge_only=True)))["edge_boost"] > 3
    assert measure_knobs(_full_pitch(_gappy(edge_only=False)))["edge_boost"] < 1.5


def test_measure_offpitch_and_players():
    from mtah.degrade import measure_knobs

    track = _full_pitch(_gappy(edge_only=False))
    knobs = measure_knobs(track)
    assert knobs["offpitch_visible"] is False
    assert knobs["player_missing_frac"] == 0.0
    players = track.players.copy()
    players[:, :4] = np.nan  # 18 of 22 tracked
    fewer = MatchTracking(players, track.team_of_slot, track.ball, track.periods, track.pitch)
    assert abs(measure_knobs(fewer)["player_missing_frac"] - 4 / 22) < 1e-6
    assert set(knobs) == {"edge_boost", "slow_boost", "offpitch_visible", "player_missing_frac"}
