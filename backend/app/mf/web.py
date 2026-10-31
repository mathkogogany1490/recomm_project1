from fastapi import APIRouter, HTTPException, Query

from app.mf import service
from app.mf.schema import (
    MfKpiResponse,
    MfRecommendationsResponse,
)


router = APIRouter(
    prefix="/mf",
    tags=["MF"],
)


@router.get(
    "/kpi",
    response_model=MfKpiResponse,
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
    response_model=MfRecommendationsResponse,
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