"""Registry of predictors: name -> Callable[[MatchTracking], np.ndarray of H/A/D/X]."""

from functools import partial

from mtah.predictors.baseline import nearest_player

PREDICTORS = {
    "baseline25": partial(nearest_player, window=25),
    "baseline50": partial(nearest_player, window=50),
    "baseline125": partial(nearest_player, window=125),
}
