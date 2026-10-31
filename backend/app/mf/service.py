from functools import lru_cache
from pathlib import Path
import math
import os
import tempfile

import numpy as np
import torch
import torch.nn.functional as F

from tqdm import tqdm

from app.mf import repository
from app.mf.model import MatrixFactorization


FACTORS = 64
EPOCHS = 20
BATCH_SIZE = 8192
LEARNING_RATE = 0.003
WEIGHT_DECAY = 1e-5
VALIDATION_RATIO = 0.2
SEED = 42

MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "checkpoint"
    / "mf_model.pt"
)

GENRE_KO = {
    "Action": "액션",
    "Adventure": "모험",
    "Animation": "애니메이션",
    "Children": "어린이",
    "Children's": "어린이",
    "Comedy": "코미디",
    "Crime": "범죄",
    "Documentary": "다큐멘터리",
    "Drama": "드라마",
    "Fantasy": "판타지",
    "Film-Noir": "필름 누아르",
    "Horror": "공포",
    "Musical": "뮤지컬",
    "Mystery": "미스터리",
    "Romance": "로맨스",
    "Sci-Fi": "SF",
    "Thriller": "스릴러",
    "War": "전쟁",
    "Western": "서부극",
    "(no genres listed)": "장르 미상",
}


def translate_genres(value: str) -> list[str]:
    if not value:
        return []

    return [
        GENRE_KO.get(part.strip(), part.strip())
        for part in value.split("|")
    ]


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")

    if (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    ):
        return torch.device("mps")

    return torch.device("cpu")


def read_ratings():
    user_parts = []
    movie_parts = []
    rating_parts = []

    for batch in tqdm(
        repository.iter_ratings(),
        desc="PostgreSQL 평점 조회",
        unit="batch",
    ):
        if len(batch) == 0:
            continue

        user_parts.append(
            batch[:, 0].astype(np.int64)
        )
        movie_parts.append(
            batch[:, 1].astype(np.int64)
        )
        rating_parts.append(
            batch[:, 2].astype(np.float32)
        )

    if not rating_parts:
        raise ValueError("학습할 평점 데이터가 없습니다.")

    user_ids_raw = np.concatenate(user_parts)
    movie_ids_raw = np.concatenate(movie_parts)
    ratings = np.concatenate(rating_parts)

    del user_parts, movie_parts, rating_parts

    user_ids, user_indices = np.unique(
        user_ids_raw,
        return_inverse=True,
    )

    movie_ids, movie_indices = np.unique(
        movie_ids_raw,
        return_inverse=True,
    )

    del user_ids_raw, movie_ids_raw

    return (
        user_ids,
        movie_ids,
        user_indices.astype(np.int32),
        movie_indices.astype(np.int32),
        ratings,
    )


def make_split(
    user_indices,
    movie_indices,
    ratings,
):
    """
    사용자와 영화의 첫 관측 평점을 학습에 남기고
    나머지 평점에서 검증 데이터를 선택합니다.

    따라서 검증 데이터의 사용자/영화가
    학습 데이터에 한 번 이상 등장합니다.
    """
    count = len(ratings)

    rng = np.random.default_rng(SEED)

    # 사용자와 영화의 최초 관측 행
    # np.unique의 return_index는 최초 위치를 반환
    _, first_users = np.unique(
        user_indices,
        return_index=True,
    )
    _, first_movies = np.unique(
        movie_indices,
        return_index=True,
    )

    protected = np.zeros(count, dtype=bool)
    protected[first_users] = True
    protected[first_movies] = True

    eligible = np.flatnonzero(~protected)

    validation_size = min(
        int(count * VALIDATION_RATIO),
        len(eligible),
    )

    if validation_size == 0:
        raise ValueError(
            "검증 데이터를 확보할 수 없습니다."
        )

    validation_indices = rng.choice(
        eligible,
        size=validation_size,
        replace=False,
    )

    train_mask = np.ones(count, dtype=bool)
    train_mask[validation_indices] = False

    train_indices = np.flatnonzero(train_mask)

    return train_indices, validation_indices


def evaluate(
    model,
    user_indices,
    movie_indices,
    ratings,
    indices,
    device,
):
    model.eval()

    absolute_error_sum = 0.0
    squared_error_sum = 0.0
    evaluated_count = 0

    with torch.inference_mode():
        for start in range(0, len(indices), BATCH_SIZE):
            batch_ids = indices[start:start + BATCH_SIZE]

            users = torch.as_tensor(
                user_indices[batch_ids].astype(np.int64),
                dtype=torch.long,
                device=device,
            )

            movies = torch.as_tensor(
                movie_indices[batch_ids].astype(np.int64),
                dtype=torch.long,
                device=device,
            )

            actual = torch.as_tensor(
                ratings[batch_ids],
                dtype=torch.float32,
                device=device,
            )

            predicted = model(users, movies).clamp(1.0, 5.0)

            # GPU/MPS에서 CPU로 옮긴 후 float64 계산
            predicted_cpu = (
                predicted.detach()
                .cpu()
                .numpy()
                .astype(np.float64)
            )

            actual_cpu = (
                actual.detach()
                .cpu()
                .numpy()
                .astype(np.float64)
            )

            errors = actual_cpu - predicted_cpu

            absolute_error_sum += float(
                np.abs(errors).sum(dtype=np.float64)
            )

            squared_error_sum += float(
                np.square(errors).sum(dtype=np.float64)
            )

            evaluated_count += len(batch_ids)

    mae = absolute_error_sum / evaluated_count
    mse = squared_error_sum / evaluated_count
    rmse = math.sqrt(mse)

    return {
        "mae": float(mae),
        "mse": float(mse),
        "rmse": float(rmse),
    }


def train_model():
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    device = get_device()

    print(f"[MF] 학습 장치: {device}")

    if device.type == "cuda":
        print(
            "[MF] GPU:",
            torch.cuda.get_device_name(0),
        )

    (
        user_ids,
        movie_ids,
        user_indices,
        movie_indices,
        ratings,
    ) = read_ratings()

    train_indices, validation_indices = make_split(
        user_indices,
        movie_indices,
        ratings,
    )

    user_count = len(user_ids)
    movie_count = len(movie_ids)

    global_mean = float(
        ratings[train_indices].mean(dtype=np.float64)
    )

    print(f"[MF] 사용자: {user_count:,}")
    print(f"[MF] 영화: {movie_count:,}")
    print(f"[MF] 학습 평점: {len(train_indices):,}")
    print(f"[MF] 검증 평점: {len(validation_indices):,}")

    model = MatrixFactorization(
        user_count=user_count,
        movie_count=movie_count,
        factors=FACTORS,
        global_mean=global_mean,
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
    )

    rng = np.random.default_rng(SEED)

    best_rmse = float("inf")
    best_state = None
    best_metrics = None
    best_epoch = 0

    for epoch in range(1, EPOCHS + 1):
        model.train()

        shuffled = rng.permutation(train_indices)

        epoch_loss_sum = 0.0
        processed = 0

        progress = tqdm(
            range(0, len(shuffled), BATCH_SIZE),
            desc=f"MF Epoch {epoch}/{EPOCHS}",
            unit="batch",
        )

        for start in progress:
            batch_ids = shuffled[
                start:start + BATCH_SIZE
            ]

            users = torch.as_tensor(
                user_indices[batch_ids].astype(np.int64),
                dtype=torch.long,
                device=device,
            )

            movies = torch.as_tensor(
                movie_indices[batch_ids].astype(np.int64),
                dtype=torch.long,
                device=device,
            )

            actual = torch.as_tensor(
                ratings[batch_ids],
                dtype=torch.float32,
                device=device,
            )

            optimizer.zero_grad(set_to_none=True)

            predicted = model(users, movies)

            loss = F.mse_loss(predicted, actual)

            loss.backward()
            optimizer.step()

            epoch_loss_sum += (
                float(loss.detach().cpu()) * len(batch_ids)
            )
            processed += len(batch_ids)

            progress.set_postfix(
                train_mse=f"{epoch_loss_sum / processed:.4f}"
            )

        metrics = evaluate(
            model,
            user_indices,
            movie_indices,
            ratings,
            validation_indices,
            device,
        )

        print(
            f"[MF] Epoch {epoch}/{EPOCHS} "
            f"Validation MAE={metrics['mae']:.4f}, "
            f"MSE={metrics['mse']:.4f}, "
            f"RMSE={metrics['rmse']:.4f}"
        )

        if metrics["rmse"] < best_rmse:
            best_rmse = metrics["rmse"]
            best_metrics = metrics
            best_epoch = epoch

            # 가장 좋은 모델을 CPU 메모리에 보관
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }

    if best_state is None:
        raise RuntimeError("학습된 모델이 없습니다.")

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    checkpoint = {
        "state_dict": best_state,
        "user_ids": torch.from_numpy(
            user_ids.copy()
        ),
        "movie_ids": torch.from_numpy(
            movie_ids.copy()
        ),
        "factors": FACTORS,
        "epochs": best_epoch,
        "train_count": len(train_indices),
        "validation_count": len(validation_indices),
        "mae": best_metrics["mae"],
        "mse": best_metrics["mse"],
        "rmse": best_metrics["rmse"],
        "evaluation": "validation",
    }

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            dir=MODEL_PATH.parent,
            suffix=".pt",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

        torch.save(checkpoint, temp_path)

        os.replace(temp_path, MODEL_PATH)

    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    load_model.cache_clear()

    print("\n[MF] 학습 완료")
    print(f"최적 Epoch: {best_epoch}")
    print(f"MAE : {best_metrics['mae']:.4f}")
    print(f"MSE : {best_metrics['mse']:.4f}")
    print(f"RMSE: {best_metrics['rmse']:.4f}")
    print(f"저장: {MODEL_PATH}")

    return best_metrics


@lru_cache(maxsize=1)
def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "MF 모델이 없습니다. 먼저 학습하세요."
        )

    checkpoint = torch.load(
        MODEL_PATH,
        map_location="cpu",
        weights_only=True,
    )

    user_ids = checkpoint["user_ids"].numpy()
    movie_ids = checkpoint["movie_ids"].numpy()

    model = MatrixFactorization(
        user_count=len(user_ids),
        movie_count=len(movie_ids),
        factors=int(checkpoint["factors"]),
    )

    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    return {
        "model": model,
        "user_ids": user_ids,
        "movie_ids": movie_ids,
        "checkpoint": checkpoint,
    }


def get_kpi():
    loaded = load_model()
    checkpoint = loaded["checkpoint"]

    return {
        "mae": checkpoint["mae"],
        "mse": checkpoint["mse"],
        "rmse": checkpoint["rmse"],
        "train_count": checkpoint["train_count"],
        "validation_count": checkpoint["validation_count"],
        "user_count": len(loaded["user_ids"]),
        "movie_count": len(loaded["movie_ids"]),
        "factors": checkpoint["factors"],
        "epochs": checkpoint["epochs"],
        "device": get_device().type,
        "evaluation": checkpoint["evaluation"],
    }


def recommend_for_user(user_id: int):
    loaded = load_model()

    model = loaded["model"]
    user_ids = loaded["user_ids"]
    movie_ids = loaded["movie_ids"]

    user_index = int(np.searchsorted(user_ids, user_id))

    if (
        user_index >= len(user_ids)
        or user_ids[user_index] != user_id
    ):
        raise ValueError(
            f"학습 모델에 사용자 {user_id}가 없습니다."
        )

    # 추론은 CPU에서 수행합니다.
    # 영화 수 길이의 벡터만 계산하므로 메모리 부담이 작습니다.
    with torch.inference_mode():
        user_vector = model.user_embedding.weight[
            user_index
        ]

        movie_vectors = model.movie_embedding.weight

        user_bias = model.user_bias.weight[
            user_index, 0
        ]

        movie_bias = model.movie_bias.weight.squeeze(-1)

        predictions = (
            movie_vectors @ user_vector
            + user_bias
            + movie_bias
            + model.global_mean
        )

        predictions = (
            predictions.clamp(1.0, 5.0)
            .cpu()
            .numpy()
        )

    seen_ids = repository.get_seen_movie_ids(user_id)

    candidate_indices = np.array(
        [
            index
            for index, movie_id in enumerate(movie_ids)
            if int(movie_id) not in seen_ids
        ],
        dtype=np.int64,
    )

    if len(candidate_indices) == 0:
        return {
            "user_id": user_id,
            "recommendations": [],
        }

    candidate_scores = predictions[candidate_indices]

    # 예측 평점 내림차순, 동점은 영화 ID 오름차순
    order = np.lexsort(
        (
            movie_ids[candidate_indices],
            -candidate_scores,
        )
    )

    ranked_indices = candidate_indices[order]

    # 영화 정보가 없을 때를 대비해 후보를 추가 조회
    # 일반적으로 상위 5개만으로 충분합니다.
    recommendations = []

    for start in range(0, len(ranked_indices), 100):
        indices = ranked_indices[start:start + 100]

        ids = [
            int(movie_ids[index])
            for index in indices
        ]

        details = repository.get_movie_details(ids)

        for index in indices:
            movie_id = int(movie_ids[index])
            movie = details.get(movie_id)

            if movie is None:
                continue

            recommendations.append({
                "rank": len(recommendations) + 1,
                "movie_id": movie_id,
                "title": movie["title"],
                "genres": translate_genres(movie["genres"]),
                "predicted_rating": round(
                    float(predictions[index]),
                    4,
                ),
            })

            if len(recommendations) == 5:
                break

        if len(recommendations) == 5:
            break

    return {
        "user_id": user_id,
        "recommendations": recommendations,
    }