from fastapi import APIRouter, HTTPException, Query

from app.transformer import service
from app.transformer.schema import (
    TransformerKpiResponse,
    TransformerRecommendationsResponse,
)


router = APIRouter(
    prefix="/transformer",
    tags=["Transformer"],
)


@router.get(
    "/kpi",
    response_model=TransformerKpiResponse,
)
def get_kpi():
    try:
        return service.get_kpi()

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )


@router.get(
    "/recommendations",
    response_model=TransformerRecommendationsResponse,
)
def get_recommendations(
    user_id: int = Query(..., ge=1),
):
    try:
        return service.recommend_for_user(user_id)

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )