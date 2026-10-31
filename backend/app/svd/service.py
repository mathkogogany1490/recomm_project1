from functools import lru_cache
from pathlib import Path
import os
import tempfile

import numpy as np

from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

from app.svd import repository
from app.svd.model import SvdModel


FACTORS = 30
PREDICTION_BATCH = 100000

MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "checkpoint"
    / "svd_model.npz"
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


def translate_genres(genres: str) -> list[str]:
    if not genres:
        return []

    return [
        GENRE_KO.get(genre.strip(), genre.strip())
        for genre in genres.split("|")
    ]


def train_model():
    print("[SVD] PostgreSQL 평점 조회 시작")

    user_parts = []
    movie_parts = []
    rating_parts = []

    for batch in repository.iter_ratings():
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

    user_indices = user_indices.astype(np.int32)
    movie_indices = movie_indices.astype(np.int32)

    user_count = len(user_ids)
    movie_count = len(movie_ids)
    rating_count = len(ratings)

    k = min(
        FACTORS,
        user_count - 1,
        movie_count - 1,
    )

    if k < 1:
        raise ValueError(
            "SVD 학습에는 사용자와 영화가 각각 2개 이상 필요합니다."
        )

    print(
        f"[SVD] 사용자={user_count:,}, "
        f"영화={movie_count:,}, "
        f"평점={rating_count:,}, "
        f"잠재요인={k}"
    )

    # 고객 × 영화 밀집 행렬을 만들지 않습니다.
    sparse_matrix = csr_matrix(
        (
            ratings,
            (user_indices, movie_indices),
        ),
        shape=(user_count, movie_count),
        dtype=np.float32,
    )

    print("[SVD] 희소 행렬 분해 시작")

    U, singular_values, Vt = svds(
        sparse_matrix,
        k=k,
        which="LM",
        random_state=42,
    )

    order = np.argsort(singular_values)[::-1]

    U = U[:, order]
    singular_values = singular_values[order]
    Vt = Vt[order, :]

    sqrt_s = np.sqrt(singular_values)

    user_factors = (
        U * sqrt_s
    ).astype(np.float32)

    movie_factors = (
        Vt.T * sqrt_s
    ).astype(np.float32)

    del sparse_matrix, U, Vt

    print("[SVD] 평점 예측 및 KPI 계산")

    absolute_error_sum = 0.0
    squared_error_sum = 0.0

    for start in range(
        0,
        rating_count,
        PREDICTION_BATCH,
    ):
        end = min(
            start + PREDICTION_BATCH,
            rating_count,
        )

        u = user_indices[start:end]
        m = movie_indices[start:end]

        predicted = np.einsum(
            "ij,ij->i",
            user_factors[u],
            movie_factors[m],
        )

        predicted = np.clip(
            predicted,
            1.0,
            5.0,
        )

        actual = ratings[start:end].astype(np.float64)

        errors = actual - predicted

        absolute_error_sum += np.abs(errors).sum(
            dtype=np.float64
        )

        squared_error_sum += np.square(errors).sum(
            dtype=np.float64
        )

    mae = absolute_error_sum / rating_count
    mse = squared_error_sum / rating_count
    rmse = float(np.sqrt(mse))

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 임시 파일을 저장한 뒤 원자적으로 교체
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            dir=MODEL_PATH.parent,
            suffix=".npz",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

        np.savez_compressed(
            temp_path,
            user_ids=user_ids,
            movie_ids=movie_ids,
            user_factors=user_factors,
            movie_factors=movie_factors,
            mae=np.float64(mae),
            mse=np.float64(mse),
            rmse=np.float64(rmse),
            rating_count=np.int64(rating_count),
            factors=np.int64(k),
        )

        os.replace(temp_path, MODEL_PATH)

    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    load_model.cache_clear()

    print("[SVD] 학습 완료")
    print(f"MAE  : {mae:.4f}")
    print(f"MSE  : {mse:.4f}")
    print(f"RMSE : {rmse:.4f}")
    print(f"모델 : {MODEL_PATH}")

    return {
        "mae": float(mae),
        "mse": float(mse),
        "rmse": float(rmse),
    }


@lru_cache(maxsize=1)
def load_model() -> SvdModel:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "SVD 모델이 없습니다. 먼저 학습을 실행하세요."
        )

    with np.load(
        MODEL_PATH,
        allow_pickle=False,
    ) as data:
        return SvdModel(
            user_ids=data["user_ids"],
            movie_ids=data["movie_ids"],
            user_factors=data["user_factors"],
            movie_factors=data["movie_factors"],
            mae=float(data["mae"]),
            mse=float(data["mse"]),
            rmse=float(data["rmse"]),
            rating_count=int(data["rating_count"]),
            factors=int(data["factors"]),
        )


def get_kpi():
    model = load_model()

    return {
        "mae": model.mae,
        "mse": model.mse,
        "rmse": model.rmse,
        "rating_count": model.rating_count,
        "user_count": len(model.user_ids),
        "movie_count": len(model.movie_ids),
        "factors": model.factors,
        "evaluation": "training",
    }


def recommend_for_user(user_id: int):
    model = load_model()

    # np.unique로 정렬된 사용자 ID를 저장했으므로
    # 이진 탐색으로 인덱스를 찾습니다.
    user_index = np.searchsorted(
        model.user_ids,
        user_id,
    )

    if (
        user_index >= len(model.user_ids)
        or model.user_ids[user_index] != user_id
    ):
        raise ValueError(
            f"학습 모델에 사용자 {user_id}가 없습니다."
        )

    user_vector = model.user_factors[user_index]

    # 모든 영화의 예측 평점 계산
    # 결과는 영화 개수 길이의 1차원 배열입니다.
    predictions = (
        model.movie_factors @ user_vector
    )

    predictions = np.clip(
        predictions,
        1.0,
        5.0,
    )

    # 이미 평가한 영화 제외
    seen_ids = repository.get_seen_movie_ids(user_id)

    # 실제 영화 테이블에 존재하는 영화만 추천
    available_ids = repository.get_all_movie_ids()

    candidates = [
        i
        for i, movie_id in enumerate(model.movie_ids)
        if int(movie_id) not in seen_ids
        and int(movie_id) in available_ids
    ]

    if not candidates:
        return {
            "user_id": user_id,
            "recommendations": [],
        }

    candidates = np.asarray(
        candidates,
        dtype=np.int64,
    )

    candidate_scores = predictions[candidates]

    # 점수가 같을 때 영화 ID 오름차순
    order = np.lexsort(
        (
            model.movie_ids[candidates],
            -candidate_scores,
        )
    )

    top_indices = candidates[order[:5]]

    top_movie_ids = [
        int(model.movie_ids[i])
        for i in top_indices
    ]

    details = repository.get_movie_details(
        top_movie_ids
    )

    recommendations = []

    for index in top_indices:
        movie_id = int(model.movie_ids[index])
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

    return {
        "user_id": user_id,
        "recommendations": recommendations,
    }