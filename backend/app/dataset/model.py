from sqlalchemy import (
    BigInteger,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)

from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Movie(Base):
    __tablename__ = "movies"

    movie_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    genres: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )


class Rating(Base):
    __tablename__ = "ratings"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    movie_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("movies.movie_id"),
        primary_key=True,
    )

    rating: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_ratings_movie_id", "movie_id"),
    )