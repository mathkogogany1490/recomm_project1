from pydantic import BaseModel, Field


class TransformerKpiResponse(BaseModel):
    mae: float
    mse: float
    rmse: float

    train_count: int
    validation_count: int
    user_count: int
    movie_count: int

    epochs: int
    factors: int
    evaluation: str
    device: str


class TransformerRecommendationItem(BaseModel):
    rank: int = Field(ge=1, le=5)
    movie_id: int
    title: str
    genres: list[str]
    predicted_rating: float


class TransformerRecommendationsResponse(BaseModel):
    user_id: int
    recommendations: list[TransformerRecommendationItem]