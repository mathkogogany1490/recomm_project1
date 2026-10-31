from dataclasses import dataclass

import numpy as np


@dataclass
class SvdModel:
    user_ids: np.ndarray
    movie_ids: np.ndarray

    user_factors: np.ndarray
    movie_factors: np.ndarray

    mae: float
    mse: float
    rmse: float

    rating_count: int
    factors: int