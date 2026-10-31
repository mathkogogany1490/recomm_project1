import torch
from torch import nn


class RatingTransformer(nn.Module):
    def __init__(
        self,
        movie_count: int,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        max_length: int = 50,
        dropout: float = 0.1,
        global_mean: float = 3.5,
    ):
        super().__init__()

        self.max_length = max_length

        self.movie_embedding = nn.Embedding(
            movie_count + 1,
            d_model,
            padding_idx=0,
        )

        self.rating_embedding = nn.Linear(
            1,
            d_model,
        )

        self.position_embedding = nn.Embedding(
            max_length,
            d_model,
        )

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )

        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers,
            enable_nested_tensor=False,
        )

        self.target_embedding = nn.Embedding(
            movie_count + 1,
            d_model,
            padding_idx=0,
        )

        self.regressor = nn.Sequential(
            nn.Linear(d_model * 2, d_model),
            nn.ReLU(),
            nn.Linear(d_model, 1),
        )

        self.register_buffer(
            "global_mean",
            torch.tensor(
                global_mean,
                dtype=torch.float32,
            ),
        )

    def encode_history(
        self,
        movie_ids,
        ratings,
        lengths,
    ):
        batch_size, seq_len = movie_ids.shape
        device = movie_ids.device

        positions = torch.arange(
            seq_len,
            device=device,
        ).unsqueeze(0)

        x = (
            self.movie_embedding(movie_ids)
            + self.rating_embedding(
                ratings.unsqueeze(-1)
            )
            + self.position_embedding(positions)
        )

        offsets = torch.arange(
            seq_len,
            device=device,
        ).unsqueeze(0)

        padding_mask = offsets >= lengths.unsqueeze(1)

        causal_mask = torch.triu(
            torch.ones(
                seq_len,
                seq_len,
                device=device,
                dtype=torch.bool,
            ),
            diagonal=1,
        )

        encoded = self.encoder(
            x,
            mask=causal_mask,
            src_key_padding_mask=padding_mask,
        )

        last_positions = (
            lengths - 1
        ).clamp(min=0)

        context = encoded[
            torch.arange(
                batch_size,
                device=device,
            ),
            last_positions,
        ]

        return context

    def predict_from_context(
        self,
        context,
        target_movies,
    ):
        target_vectors = self.target_embedding(
            target_movies
        )

        features = torch.cat(
            [context, target_vectors],
            dim=-1,
        )

        return (
            self.regressor(features).squeeze(-1)
            + self.global_mean
        )

    def forward(
        self,
        history_movies,
        history_ratings,
        lengths,
        target_movies,
    ):
        context = self.encode_history(
            history_movies,
            history_ratings,
            lengths,
        )

        return self.predict_from_context(
            context,
            target_movies,
        )