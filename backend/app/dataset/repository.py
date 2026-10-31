from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.database import Base, engine, SessionLocal
from app.dataset.model import Movie, Rating


def create_tables():
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Movie.__table__,
            Rating.__table__,
        ],
        checkfirst=True,
    )


def insert_movies(rows):
    if not rows:
        return 0

    stmt = insert(Movie).values(rows)

    stmt = stmt.on_conflict_do_nothing(
        index_elements=[Movie.movie_id]
    )

    with SessionLocal() as db:
        result = db.execute(stmt)
        db.commit()

        return result.rowcount


def insert_ratings(rows):
    if not rows:
        return 0

    stmt = insert(Rating).values(rows)

    stmt = stmt.on_conflict_do_nothing(
        index_elements=[
            Rating.user_id,
            Rating.movie_id,
        ]
    )

    with SessionLocal() as db:
        result = db.execute(stmt)
        db.commit()

        return result.rowcount


def get_counts():
    with SessionLocal() as db:
        movie_count = db.scalar(
            select(func.count()).select_from(Movie)
        )

        rating_count = db.scalar(
            select(func.count()).select_from(Rating)
        )

    return {
        "movies": movie_count,
        "ratings": rating_count,
    }