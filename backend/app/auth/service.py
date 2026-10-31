from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from pwdlib import PasswordHash

from app.database import settings
from app.auth import repository
from app.auth.schema import (
    SignupRequest,
    VerifyEmailRequest,
    ResendCodeRequest,
    LoginRequest,
)


password_hasher = PasswordHash.recommended()

bearer_scheme = HTTPBearer(
    auto_error=False,
)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return password_hasher.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(
            minutes=settings.JWT_EXPIRE_MINUTES
        ),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def send_code(email: str):
    result = repository.issue_verification_code(email)

    if result["status"] == 1:
        raise HTTPException(
            status_code=429,
            detail=(
                f"인증번호는 {result['wait']}초 후 "
                "다시 보낼 수 있습니다."
            ),
            headers={
                "Retry-After": str(result["wait"])
            },
        )

    if result["status"] == 2:
        raise HTTPException(
            status_code=429,
            detail=(
                "시간당 인증번호 발송 횟수 "
                "5회를 초과했습니다."
            ),
            headers={
                "Retry-After": str(result["wait"])
            },
        )

    try:
        repository.send_verification_email(
            email,
            result["code"],
        )
    except Exception:
        repository.delete_verification_code(email)

        raise HTTPException(
            status_code=503,
            detail="이메일 발송에 실패했습니다.",
        )

    times = repository.get_verification_times(email)

    return {
        "message": "인증번호를 발송했습니다.",
        **times,
    }


def signup(data: SignupRequest):
    email = repository.normalize_email(str(data.email))

    existing = repository.get_user_by_email(email)

    if existing:
        raise HTTPException(
            status_code=409,
            detail="이미 가입된 이메일입니다.",
        )

    password_hash = hash_password(data.password)

    user = repository.create_user(
        email=email,
        password_hash=password_hash,
    )

    if user is None:
        raise HTTPException(
            status_code=409,
            detail="이미 가입된 이메일입니다.",
        )

    return send_code(email)


def verify_email(data: VerifyEmailRequest):
    email = repository.normalize_email(str(data.email))

    user = repository.get_user_by_email(email)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="존재하지 않는 회원입니다.",
        )

    if user.is_verified:
        raise HTTPException(
            status_code=409,
            detail="이미 인증된 이메일입니다.",
        )

    result = repository.verify_code(
        email,
        data.code,
    )

    if result == 1:
        raise HTTPException(
            status_code=400,
            detail="인증번호가 만료되었거나 존재하지 않습니다.",
        )

    if result == 2:
        raise HTTPException(
            status_code=400,
            detail="인증번호가 일치하지 않습니다.",
        )

    if result == 3:
        raise HTTPException(
            status_code=429,
            detail=(
                "인증번호 확인 횟수 5회를 초과했습니다. "
                "새 인증번호를 요청하세요."
            ),
        )

    if result != 0:
        raise HTTPException(
            status_code=400,
            detail="이메일 인증에 실패했습니다.",
        )

    updated_user = repository.mark_user_verified(email)

    if updated_user is None:
        raise HTTPException(
            status_code=404,
            detail="회원 정보를 찾을 수 없습니다.",
        )

    return {
        "message": "이메일 인증이 완료되었습니다."
    }


def resend_code(data: ResendCodeRequest):
    email = repository.normalize_email(str(data.email))

    user = repository.get_user_by_email(email)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="존재하지 않는 회원입니다.",
        )

    if user.is_verified:
        raise HTTPException(
            status_code=409,
            detail="이미 인증된 이메일입니다.",
        )

    return send_code(email)


def login(data: LoginRequest):
    email = repository.normalize_email(str(data.email))

    user = repository.get_user_by_email(email)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="이메일 인증을 완료해 주세요.",
        )

    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증이 필요하거나 토큰이 만료되었습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise auth_error

    if credentials.scheme.lower() != "bearer":
        raise auth_error

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )

        user_id = int(payload["sub"])

    except (
        InvalidTokenError,
        ValueError,
        TypeError,
        KeyError,
    ):
        raise auth_error

    user = repository.get_user_by_id(user_id)

    if user is None or not user.is_verified:
        raise auth_error

    return user


def get_me(user):
    return user