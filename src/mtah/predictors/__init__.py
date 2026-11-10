"""Registry of predictors: name -> Callable[[MatchTracking], np.ndarray of H/A/D/X]."""

from functools import partial

from mtah.predictors.baseline import nearest_player
from mtah.predictors.learned import predict_learned

PREDICTORS = {
    "baseline25": partial(nearest_player, window=25),
    "baseline50": partial(nearest_player, window=50),
    "baseline125": partial(nearest_player, window=125),
    "learned": predict_learned,  # trains on the cached IDSSE matches on first use (~1-2 min)
}
