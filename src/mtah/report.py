"""Aggregate-only reporting. Match-side code prints through here and nowhere else (rule R1)."""


def summary(name: str, scores: dict) -> str:
    return (f"{name}: spellF1 {scores['spell_f1']:.4f}  macroF1 {scores['macro_f1']:.4f}  "
            f"spells {scores['n_pred_spells']:.0f}/{scores['n_gt_spells']:.0f}  "
            f"dur {scores['mean_spell_s']:.1f}s/{scores['gt_mean_spell_s']:.1f}s")
