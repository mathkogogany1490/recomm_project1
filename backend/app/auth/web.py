from fastapi import APIRouter, Depends, status

from app.auth import service
from app.auth.schema import (
    SignupRequest,
    VerifyEmailRequest,
    ResendCodeRequest,
    LoginRequest,
    VerificationCodeResponse,
    MessageResponse,
    LoginResponse,
    UserResponse,
)


router = APIRouter(tags=["Auth"])


@router.post(
    "/users",
    response_model=VerificationCodeResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(data: SignupRequest):
    return service.signup(data)


@router.post(
    "/auth/verify-email",
    response_model=MessageResponse,
)
def verify_email(data: VerifyEmailRequest):
    return service.verify_email(data)


@router.post(
    "/auth/resend-code",
    response_model=VerificationCodeResponse,
)
def resend_code(data: ResendCodeRequest):
    return service.resend_code(data)


@router.post(
    "/auth/login",
    response_model=LoginResponse,
)
def login(data: LoginRequest):
    return service.login(data)


@router.get(
    "/users/me",
    response_model=UserResponse,
)
def get_me(
    user=Depends(service.get_current_user),
):
    return service.get_me(user)