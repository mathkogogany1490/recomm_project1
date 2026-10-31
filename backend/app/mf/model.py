import torch
from torch import nn


class MatrixFactorization(nn.Module):
    def __init__(
        self,
        user_count: int,
        movie_count: int,
        factors: int = 64,
        global_mean: float = 3.5,
    ):
        super().__init__()

        self.user_embedding = nn.Embedding(
            user_count,
            factors,
        )

        self.movie_embedding = nn.Embedding(
            movie_count,
            factors,
        )

        self.user_bias = nn.Embedding(user_count, 1)
        self.movie_bias = nn.Embedding(movie_count, 1)

        self.register_buffer(
            "global_mean",
            torch.tensor(global_mean, dtype=torch.float32),
        )

        nn.init.normal_(
            self.user_embedding.weight,
            mean=0.0,
            std=0.05,
        )

        nn.init.normal_(
            self.movie_embedding.weight,
            mean=0.0,
            std=0.05,
        )

        nn.init.zeros_(self.user_bias.weight)
        nn.init.zeros_(self.movie_bias.weight)

    def forward(self, user_indices, movie_indices):
        user_vectors = self.user_embedding(user_indices)
        movie_vectors = self.movie_embedding(movie_indices)

        interaction = (
            user_vectors * movie_vectors
        ).sum(dim=1)

        user_bias = self.user_bias(
            user_indices
        ).squeeze(-1)

        movie_bias = self.movie_bias(
            movie_indices
        ).squeeze(-1)

        return (
            self.global_mean
            + user_bias
            + movie_bias
            + interaction
        )