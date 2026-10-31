from functools import lru_cache
from pathlib import Path
import math
import os
import tempfile

import numpy as np
import torch
import torch.nn.functional as F

from tqdm import tqdm

from app.transformer import repository
from app.transformer.model import RatingTransformer


SEED = 42

MAX_LENGTH = 50
D_MODEL = 64
NHEAD = 4
NUM_LAYERS = 2

EPOCHS = 3
BATCH_SIZE = 512

LEARNING_RATE = 0.001
WEIGHT_DECAY = 1e-5
VALIDATION_RATIO = 0.1

MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "checkpoint"
    / "transformer_model.pt"
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


def translate_genres(value):
    if not value:
        return []

    return [
        GENRE_KO.get(x.strip(), x.strip())
        for x in value.split("|")
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


# ------------------------------------------------------------
# DB 데이터 로딩
# ------------------------------------------------------------

def load_histories():
    histories = {}
    movie_ids = set()
    rating_count = 0

    for batch in tqdm(
        repository.iter_ratings(),
        desc="Transformer 평점 조회",
        unit="batch",
    ):
        for user_id, movie_id, rating in batch:
            user_id = int(user_id)
            movie_id = int(movie_id)

            if user_id not in histories:
                histories[user_id] = []

            histories[user_id].append(
                (movie_id, float(rating))
            )

            movie_ids.add(movie_id)
            rating_count += 1

    if not histories:
        raise ValueError("평점 데이터가 없습니다.")

    # timestamp 없이 영화 ID 오름차순 사용
    for records in histories.values():
        records.sort(key=lambda x: x[0])

    print(f"[Transformer] 사용자: {len(histories):,}")
    print(f"[Transformer] 영화: {len(movie_ids):,}")
    print(f"[Transformer] 평점: {rating_count:,}")
    print("[Transformer] 정렬: movie_id 오름차순")

    return histories, np.asarray(
        sorted(movie_ids),
        dtype=np.int64,
    )


# ------------------------------------------------------------
# 연속 텐서 데이터 생성
# ------------------------------------------------------------

def prepare_tensor_data(
    histories,
    movie_to_index,
    device,
):
    """
    관측 평점만 사용합니다.

    movie_data: 모든 사용자 평점의 영화 인덱스
    rating_data: 모든 사용자 평점의 실제 평점

    train_targets / validation_targets:
      [target_position, user_start_position]

    전체 고객 × 영화 피벗은 생성하지 않습니다.
    """

    total_ratings = sum(
        len(records)
        for records in histories.values()
        if len(records) >= 2
    )

    total_train = 0
    total_validation = 0

    for records in histories.values():
        n = len(records)

        if n < 2:
            continue

        validation_count = max(
            1,
            math.ceil(n * VALIDATION_RATIO),
        )

        split = max(1, n - validation_count)

        total_train += max(0, split - 1)
        total_validation += n - split

    # NumPy 배열을 정확한 크기로 미리 할당
    movie_data = np.empty(
        total_ratings,
        dtype=np.int32,
    )

    rating_data = np.empty(
        total_ratings,
        dtype=np.float32,
    )

    train_targets = np.empty(
        (total_train, 2),
        dtype=np.int32,
    )

    validation_targets = np.empty(
        (total_validation, 2),
        dtype=np.int32,
    )

    offset = 0
    train_offset = 0
    validation_offset = 0

    train_rating_sum = 0.0
    train_rating_count = 0

    for records in histories.values():
        n = len(records)

        if n < 2:
            continue

        validation_count = max(
            1,
            math.ceil(n * VALIDATION_RATIO),
        )

        split = max(1, n - validation_count)

        for pos, (movie_id, rating) in enumerate(records):
            movie_data[offset + pos] = (
                movie_to_index[movie_id]
            )

            rating_data[offset + pos] = rating

        # 학습 구간 평균
        train_rating_sum += float(
            rating_data[offset:offset + split]
            .sum(dtype=np.float64)
        )

        train_rating_count += split

        # 학습 대상 위치
        train_count = max(0, split - 1)

        if train_count:
            train_targets[
                train_offset:train_offset + train_count,
                0,
            ] = np.arange(
                offset + 1,
                offset + split,
                dtype=np.int32,
            )

            train_targets[
                train_offset:train_offset + train_count,
                1,
            ] = offset

            train_offset += train_count

        # 검증 대상 위치
        valid_count = n - split

        validation_targets[
            validation_offset:validation_offset + valid_count,
            0,
        ] = np.arange(
            offset + split,
            offset + n,
            dtype=np.int32,
        )

        validation_targets[
            validation_offset:validation_offset + valid_count,
            1,
        ] = offset

        validation_offset += valid_count
        offset += n

    if total_train == 0:
        raise ValueError("학습 데이터가 없습니다.")

    if total_validation == 0:
        raise ValueError("검증 데이터가 없습니다.")

    global_mean = (
        train_rating_sum / train_rating_count
    )

    print("[Transformer] 텐서 변환 시작")

    movie_tensor = torch.from_numpy(
        movie_data
    ).to(device)

    rating_tensor = torch.from_numpy(
        rating_data
    ).to(device)

    train_tensor = torch.from_numpy(
        train_targets
    ).to(device)

    validation_tensor = torch.from_numpy(
        validation_targets
    ).to(device)

    print("[Transformer] 텐서 변환 완료")

    return {
        "movies": movie_tensor,
        "ratings": rating_tensor,
        "train_targets": train_tensor,
        "validation_targets": validation_tensor,
        "global_mean": global_mean,
        "train_count": total_train,
        "validation_count": total_validation,
    }


# ------------------------------------------------------------
# GPU/MPS/CPU에서 시퀀스 배치 생성
# ------------------------------------------------------------

def make_batch(
    movie_tensor,
    rating_tensor,
    target_pairs,
):
    device = movie_tensor.device

    target_positions = (
        target_pairs[:, 0].long()
    )

    user_starts = (
        target_pairs[:, 1].long()
    )

    lengths = torch.clamp(
        target_positions - user_starts,
        min=1,
        max=MAX_LENGTH,
    )

    offsets = torch.arange(
        MAX_LENGTH,
        device=device,
        dtype=torch.long,
    )

    history_positions = (
        target_positions[:, None]
        - lengths[:, None]
        + offsets[None, :]
    )

    valid = (
        offsets[None, :]
        < lengths[:, None]
    )

    safe_positions = history_positions.clamp(
        min=0,
        max=movie_tensor.numel() - 1,
    )

    history_movies = movie_tensor[
        safe_positions
    ].long()

    history_ratings = rating_tensor[
        safe_positions
    ]

    history_movies = history_movies.masked_fill(
        ~valid,
        0,
    )

    history_ratings = history_ratings.masked_fill(
        ~valid,
        0.0,
    )

    target_movies = movie_tensor[
        target_positions
    ].long()

    actual = rating_tensor[
        target_positions
    ]

    return (
        history_movies,
        history_ratings,
        lengths,
        target_movies,
        actual,
    )


# ------------------------------------------------------------
# 한 Epoch 학습
# ------------------------------------------------------------

def train_epoch(
    model,
    optimizer,
    data,
    epoch,
):
    model.train()

    train_targets = data["train_targets"]

    device = train_targets.device

    shuffled = torch.randperm(
        len(train_targets),
        device=device,
    )

    loss_sum = 0.0
    processed = 0

    progress = tqdm(
        range(0, len(shuffled), BATCH_SIZE),
        desc=f"Transformer Epoch {epoch}/{EPOCHS}",
        unit="batch",
    )

    for start in progress:
        batch_indices = shuffled[
            start:start + BATCH_SIZE
        ]

        target_pairs = train_targets[
            batch_indices
        ]

        (
            history_movies,
            history_ratings,
            lengths,
            target_movies,
            actual,
        ) = make_batch(
            data["movies"],
            data["ratings"],
            target_pairs,
        )

        optimizer.zero_grad(set_to_none=True)

        predicted = model(
            history_movies,
            history_ratings,
            lengths,
            target_movies,
        )

        loss = F.mse_loss(
            predicted,
            actual,
        )

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0,
        )

        optimizer.step()

        batch_count = len(actual)

        loss_sum += (
            float(loss.detach().cpu())
            * batch_count
        )

        processed += batch_count

        if processed % (BATCH_SIZE * 50) < BATCH_SIZE:
            progress.set_postfix(
                train_mse=f"{loss_sum / processed:.4f}"
            )

    return loss_sum / processed


# ------------------------------------------------------------
# 검증
# ------------------------------------------------------------

def evaluate(model, data):
    model.eval()

    validation_targets = data["validation_targets"]

    absolute_error_sum = 0.0
    squared_error_sum = 0.0
    total_count = 0

    with torch.inference_mode():
        progress = tqdm(
            range(
                0,
                len(validation_targets),
                BATCH_SIZE,
            ),
            desc="Transformer 검증",
            unit="batch",
            leave=False,
        )

        for start in progress:
            target_pairs = validation_targets[
                start:start + BATCH_SIZE
            ]

            (
                history_movies,
                history_ratings,
                lengths,
                target_movies,
                actual,
            ) = make_batch(
                data["movies"],
                data["ratings"],
                target_pairs,
            )

            predicted = model(
                history_movies,
                history_ratings,
                lengths,
                target_movies,
            ).clamp(1.0, 5.0)

            # CPU에서 float64 오차 계산
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

            total_count += len(errors)

    mae = absolute_error_sum / total_count
    mse = squared_error_sum / total_count

    return {
        "mae": float(mae),
        "mse": float(mse),
        "rmse": float(math.sqrt(mse)),
    }


# ------------------------------------------------------------
# 전체 학습
# ------------------------------------------------------------

def train_model():
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    device = get_device()

    print(f"[Transformer] 학습 장치: {device}")

    if device.type == "cuda":
        print(
            "[Transformer] GPU:",
            torch.cuda.get_device_name(0),
        )

    histories, movie_ids = load_histories()

    movie_to_index = {
        int(movie_id): index + 1
        for index, movie_id in enumerate(movie_ids)
    }

    data = prepare_tensor_data(
        histories,
        movie_to_index,
        device,
    )

    print(
        f"[Transformer] 학습 샘플: "
        f"{data['train_count']:,}"
    )

    print(
        f"[Transformer] 검증 샘플: "
        f"{data['validation_count']:,}"
    )

    model = RatingTransformer(
        movie_count=len(movie_ids),
        d_model=D_MODEL,
        nhead=NHEAD,
        num_layers=NUM_LAYERS,
        max_length=MAX_LENGTH,
        global_mean=data["global_mean"],
    ).to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
    )

    best_rmse = float("inf")
    best_metrics = None
    best_state = None
    best_epoch = 0

    for epoch in range(1, EPOCHS + 1):
        train_mse = train_epoch(
            model,
            optimizer,
            data,
            epoch,
        )

        metrics = evaluate(
            model,
            data,
        )

        print(
            f"[Transformer] Epoch {epoch}/{EPOCHS} "
            f"Train MSE={train_mse:.4f} "
            f"MAE={metrics['mae']:.4f} "
            f"MSE={metrics['mse']:.4f} "
            f"RMSE={metrics['rmse']:.4f}"
        )

        if metrics["rmse"] < best_rmse:
            best_rmse = metrics["rmse"]
            best_metrics = metrics
            best_epoch = epoch

            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }

    if best_state is None:
        raise RuntimeError("모델 학습에 실패했습니다.")

    checkpoint = {
        "state_dict": best_state,
        "movie_ids": torch.from_numpy(
            movie_ids.copy()
        ),
        "d_model": D_MODEL,
        "nhead": NHEAD,
        "num_layers": NUM_LAYERS,
        "max_length": MAX_LENGTH,
        "epochs": best_epoch,
        "user_count": len(histories),
        "train_count": data["train_count"],
        "validation_count": data["validation_count"],
        "mae": best_metrics["mae"],
        "mse": best_metrics["mse"],
        "rmse": best_metrics["rmse"],
        "evaluation": "validation",
    }

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    print("\n[Transformer] 학습 완료")
    print(f"최적 Epoch: {best_epoch}")
    print(f"MAE : {best_metrics['mae']:.4f}")
    print(f"MSE : {best_metrics['mse']:.4f}")
    print(f"RMSE: {best_metrics['rmse']:.4f}")
    print(f"저장: {MODEL_PATH}")

    return best_metrics


# ------------------------------------------------------------
# 모델 로딩
# ------------------------------------------------------------

@lru_cache(maxsize=1)
def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Transformer 모델이 없습니다. 먼저 학습하세요."
        )

    checkpoint = torch.load(
        MODEL_PATH,
        map_location="cpu",
        weights_only=True,
    )

    movie_ids = checkpoint["movie_ids"].numpy()

    model = RatingTransformer(
        movie_count=len(movie_ids),
        d_model=int(checkpoint["d_model"]),
        nhead=int(checkpoint["nhead"]),
        num_layers=int(checkpoint["num_layers"]),
        max_length=int(checkpoint["max_length"]),
    )

    model.load_state_dict(
        checkpoint["state_dict"]
    )

    model.eval()

    movie_to_index = {
        int(movie_id): index + 1
        for index, movie_id in enumerate(movie_ids)
    }

    return {
        "model": model,
        "movie_ids": movie_ids,
        "movie_to_index": movie_to_index,
        "checkpoint": checkpoint,
    }


# ------------------------------------------------------------
# KPI
# ------------------------------------------------------------

def get_kpi():
    loaded = load_model()
    checkpoint = loaded["checkpoint"]

    return {
        "mae": checkpoint["mae"],
        "mse": checkpoint["mse"],
        "rmse": checkpoint["rmse"],
        "train_count": checkpoint["train_count"],
        "validation_count": checkpoint["validation_count"],
        "user_count": checkpoint["user_count"],
        "movie_count": len(loaded["movie_ids"]),
        "epochs": checkpoint["epochs"],
        "factors": checkpoint["d_model"],
        "evaluation": checkpoint["evaluation"],
        "device": get_device().type,
    }


# ------------------------------------------------------------
# 추천
# ------------------------------------------------------------

def recommend_for_user(user_id: int):
    loaded = load_model()

    model = loaded["model"]
    movie_ids = loaded["movie_ids"]
    movie_to_index = loaded["movie_to_index"]

    history = repository.get_user_history(user_id)

    if not history:
        raise ValueError(
            f"사용자 {user_id}의 평점 기록이 없습니다."
        )

    seen_ids = repository.get_seen_movie_ids(user_id)

    known_history = [
        (movie_to_index[movie_id], rating)
        for movie_id, rating in history
        if movie_id in movie_to_index
    ]

    if not known_history:
        raise ValueError(
            "학습 모델에 포함된 평가 기록이 없습니다."
        )

    recent = known_history[-MAX_LENGTH:]

    history_movies = torch.zeros(
        (1, MAX_LENGTH),
        dtype=torch.long,
    )

    history_ratings = torch.zeros(
        (1, MAX_LENGTH),
        dtype=torch.float32,
    )

    for i, (movie_index, rating) in enumerate(recent):
        history_movies[0, i] = movie_index
        history_ratings[0, i] = rating

    lengths = torch.tensor(
        [len(recent)],
        dtype=torch.long,
    )

    with torch.inference_mode():
        context = model.encode_history(
            history_movies,
            history_ratings,
            lengths,
        )

        scores = np.empty(
            len(movie_ids),
            dtype=np.float32,
        )

        for start in range(0, len(movie_ids), 1024):
            end = min(
                start + 1024,
                len(movie_ids),
            )

            target_movies = torch.arange(
                start + 1,
                end + 1,
                dtype=torch.long,
            )

            repeated_context = context.expand(
                len(target_movies),
                -1,
            )

            predicted = model.predict_from_context(
                repeated_context,
                target_movies,
            )

            scores[start:end] = (
                predicted.clamp(1.0, 5.0)
                .cpu()
                .numpy()
            )

    candidate_indices = np.asarray(
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

    order = np.lexsort(
        (
            movie_ids[candidate_indices],
            -scores[candidate_indices],
        )
    )

    ranked_indices = candidate_indices[order]

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
                "genres": translate_genres(
                    movie["genres"]
                ),
                "predicted_rating": round(
                    float(scores[index]),
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