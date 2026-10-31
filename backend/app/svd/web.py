from fastapi import APIRouter, HTTPException, Query

from app.svd import service
from app.svd.schema import (
    SvdKpiResponse,
    SvdRecommendationsResponse,
)


router = APIRouter(
    prefix="/svd",
    tags=["SVD"],
)


@router.get(
    "/kpi",
    response_model=SvdKpiResponse,
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
    response_model=SvdRecommendationsResponse,
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