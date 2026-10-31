from pathlib import Path

import pandas as pd
from tqdm import tqdm

from app.dataset.repository import (
    create_tables,
    insert_movies,
    insert_ratings,
    get_counts,
)


DATA_DIR = Path(__file__).resolve().parents[1] / "data"

MOVIES_PATH = DATA_DIR / "movies.dat"
RATINGS_PATH = DATA_DIR / "ratings.pkl"

BATCH_SIZE = 5000


def import_movies():
    print("\n[1/3] 영화 데이터 적재")

    if not MOVIES_PATH.exists():
        raise FileNotFoundError(MOVIES_PATH)

    # MovieLens movies.dat 형식
    # movieID::title::genres
    with MOVIES_PATH.open(
        "r",
        encoding="latin-1",
    ) as file:
        total = sum(1 for _ in file)

    inserted = 0
    batch = []

    with MOVIES_PATH.open(
        "r",
        encoding="latin-1",
    ) as file:

        with tqdm(
            total=total,
            desc="영화 적재",
            unit="건",
        ) as progress:

            for line in file:
                progress.update(1)

                parts = line.rstrip("\r\n").split("::", 2)

                if len(parts) != 3:
                    continue

                movie_id, title, genres = parts

                batch.append({
                    "movie_id": int(movie_id),
                    "title": title,
                    "genres": genres,
                })

                if len(batch) >= BATCH_SIZE:
                    inserted += insert_movies(batch)
                    batch.clear()

            if batch:
                inserted += insert_movies(batch)

    print(f"영화 신규 적재: {inserted:,}건")

    return inserted


def import_ratings():
    print("\n[2/3] 평점 데이터 적재")

    if not RATINGS_PATH.exists():
        raise FileNotFoundError(RATINGS_PATH)

    df = pd.read_pickle(RATINGS_PATH)

    required = {
        "userID",
        "movieID",
        "ratings",
        "timestamp",
    }

    if not required.issubset(df.columns):
        raise ValueError(
            f"필수 컬럼 누락: {required - set(df.columns)}"
        )

    print(f"원본 평점: {len(df):,}건")

    # timestamp 기준 최신 평점 유지
    df = df.sort_values("timestamp")

    df = df.drop_duplicates(
        subset=["userID", "movieID"],
        keep="last",
    )

    df = df[[
        "userID",
        "movieID",
        "ratings",
    ]]

    print(f"중복 제거 후: {len(df):,}건")

    inserted = 0

    with tqdm(
        total=len(df),
        desc="평점 적재",
        unit="건",
    ) as progress:

        for start in range(0, len(df), BATCH_SIZE):
            chunk = df.iloc[
                start:start + BATCH_SIZE
            ]

            rows = [
                {
                    "user_id": int(user_id),
                    "movie_id": int(movie_id),
                    "rating": float(rating),
                }
                for user_id, movie_id, rating
                in chunk.itertuples(
                    index=False,
                    name=None,
                )
            ]

            inserted += insert_ratings(rows)

            progress.update(len(chunk))

    print(f"평점 신규 적재: {inserted:,}건")

    return inserted


def main():
    print("=" * 50)
    print("추천 시스템 데이터 적재 시작")
    print("=" * 50)

    # 없는 테이블만 생성
    create_tables()

    # FK 관계 때문에 영화 먼저 적재
    import_movies()

    # 평점 적재
    import_ratings()

    print("\n[3/3] PostgreSQL 데이터 수 확인")

    counts = get_counts()

    print("=" * 50)
    print(f"영화 수 : {counts['movies']:,}건")
    print(f"평점 수 : {counts['ratings']:,}건")
    print("=" * 50)

    print("데이터 적재 완료")


if __name__ == "__main__":
    main()