"""Aggregate-only reporting. Match-side code prints through here and nowhere else (rule R1)."""


def summary(name: str, scores: dict) -> str:
    return (f"{name}: spellF1 {scores['spell_f1']:.4f}  macroF1 {scores['macro_f1']:.4f}  "
            f"spells {scores['n_pred_spells']:.0f}/{scores['n_gt_spells']:.0f}  "
            f"dur {scores['mean_spell_s']:.1f}s/{scores['gt_mean_spell_s']:.1f}s")


def coverage(periods, n_frames: int, graded) -> str:
    """How much of the match the inferred periods cover, and how many graded frames fall outside
    them (those are written as D). periods are half-open, graded blocks inclusive."""
    import numpy as np

    inside = np.zeros(n_frames, dtype=bool)
    for start, stop in periods:
        inside[start:stop] = True
    is_graded = np.zeros(n_frames, dtype=bool)
    for first, last in graded:
        is_graded[first:last + 1] = True
    outside = int((is_graded & ~inside).sum())
    return (f"inferred periods: {len(periods)}, covering {100 * inside.mean():.0f}% of frames; "
            f"graded frames outside periods: {outside} of {int(is_graded.sum())} (labelled D)")
