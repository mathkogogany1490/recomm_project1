import numpy as np

from sqlalchemy import select

from app.database import SessionLocal
from app.dataset.model import Movie, Rating


def iter_ratings(batch_size: int = 50000):
    stmt = select(
        Rating.user_id,
        Rating.movie_id,
        Rating.rating,
    ).order_by(
        Rating.user_id,
        Rating.movie_id,
    )

    with SessionLocal() as db:
        result = db.execute(
            stmt.execution_options(
                stream_results=True,
                yield_per=batch_size,
            )
        )

        for partition in result.partitions(batch_size):
            yield np.asarray(
                partition,
                dtype=np.float64,
            )


def get_seen_movie_ids(user_id: int) -> set[int]:
    with SessionLocal() as db:
        stmt = select(Rating.movie_id).where(
            Rating.user_id == user_id
        )

        return set(db.scalars(stmt).all())


def get_movie_details(movie_ids: list[int]) -> dict:
    if not movie_ids:
        return {}

    with SessionLocal() as db:
        stmt = select(
            Movie.movie_id,
            Movie.title,
            Movie.genres,
        ).where(
            Movie.movie_id.in_(movie_ids)
        )

        return {
            int(movie_id): {
                "title": title,
                "genres": genres,
            }
            for movie_id, title, genres in db.execute(stmt)
        }