import hashlib
import hmac
import html
import secrets
import smtplib

from datetime import datetime, timezone, timedelta
from email.message import EmailMessage

import redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal, settings
from app.auth.model import User


CODE_TTL = 300
RESEND_COOLDOWN = 60
HOURLY_LIMIT = 5
MAX_ATTEMPTS = 5


redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def email_key(email: str) -> str:
    return hashlib.sha256(
        normalize_email(email).encode()
    ).hexdigest()


def code_hash(email: str, code: str) -> str:
    message = f"{normalize_email(email)}:{code}"

    return hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def get_user_by_email(email: str):
    with SessionLocal() as db:
        return db.scalar(
            select(User).where(
                User.email == normalize_email(email)
            )
        )


def get_user_by_id(user_id: int):
    with SessionLocal() as db:
        return db.get(User, user_id)


def create_user(email: str, password_hash: str):
    user = User(
        email=normalize_email(email),
        password_hash=password_hash,
        is_verified=False,
    )

    with SessionLocal() as db:
        db.add(user)

        try:
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError:
            db.rollback()
            return None


def mark_user_verified(email: str):
    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(
                User.email == normalize_email(email)
            )
        )

        if user is None:
            return None

        user.is_verified = True
        db.commit()
        db.refresh(user)

        return user


# Redis Lua:
# 인증번호 발급, 60초 제한, 시간당 5회 제한을
# 하나의 원자적 연산으로 처리합니다.
ISSUE_SCRIPT = """
local code_key = KEYS[1]
local cooldown_key = KEYS[2]
local hourly_key = KEYS[3]

local code_hash = ARGV[1]
local code_ttl = tonumber(ARGV[2])
local cooldown = tonumber(ARGV[3])
local hourly_limit = tonumber(ARGV[4])

local wait = redis.call("TTL", cooldown_key)

if wait > 0 then
    return {1, wait}
end

local count = tonumber(redis.call("GET", hourly_key) or "0")

if count >= hourly_limit then
    local hourly_wait = redis.call("TTL", hourly_key)
    return {2, hourly_wait}
end

local new_count = redis.call("INCR", hourly_key)

if new_count == 1 then
    redis.call("EXPIRE", hourly_key, 3600)
end

redis.call("SET", code_key, code_hash .. ":0", "EX", code_ttl)
redis.call("SET", cooldown_key, "1", "EX", cooldown)

return {0, 0}
"""


# 인증 확인도 원자적으로 처리합니다.
# 틀릴 때마다 횟수를 증가시키고
# 5회 실패하면 인증번호를 삭제합니다.
# 성공하면 인증번호를 즉시 삭제합니다.
VERIFY_SCRIPT = """
local code_key = KEYS[1]
local expected_hash = ARGV[1]
local max_attempts = tonumber(ARGV[2])

local value = redis.call("GET", code_key)

if not value then
    return 1
end

local separator = string.find(value, ":", 1, true)

if not separator then
    redis.call("DEL", code_key)
    return 1
end

local stored_hash = string.sub(value, 1, separator - 1)
local attempts = tonumber(
    string.sub(value, separator + 1)
) or 0

if attempts >= max_attempts then
    redis.call("DEL", code_key)
    return 3
end

if stored_hash == expected_hash then
    redis.call("DEL", code_key)
    return 0
end

attempts = attempts + 1

if attempts >= max_attempts then
    redis.call("DEL", code_key)
    return 3
end

local ttl = redis.call("PTTL", code_key)

if ttl <= 0 then
    redis.call("DEL", code_key)
    return 1
end

redis.call(
    "SET",
    code_key,
    stored_hash .. ":" .. attempts,
    "PX",
    ttl
)

return 2
"""


def issue_verification_code(email: str):
    key = email_key(email)

    code = f"{secrets.randbelow(1_000_000):06d}"
    hashed = code_hash(email, code)

    result = redis_client.eval(
        ISSUE_SCRIPT,
        3,
        f"auth:code:{key}",
        f"auth:cooldown:{key}",
        f"auth:hourly:{key}",
        hashed,
        CODE_TTL,
        RESEND_COOLDOWN,
        HOURLY_LIMIT,
    )

    status, wait = map(int, result)

    if status != 0:
        return {
            "status": status,
            "wait": max(wait, 0),
            "code": None,
        }

    return {
        "status": 0,
        "wait": 0,
        "code": code,
    }


def verify_code(email: str, code: str) -> int:
    key = email_key(email)

    return int(
        redis_client.eval(
            VERIFY_SCRIPT,
            1,
            f"auth:code:{key}",
            code_hash(email, code),
            MAX_ATTEMPTS,
        )
    )


def delete_verification_code(email: str):
    key = email_key(email)
    redis_client.delete(f"auth:code:{key}")


def get_verification_times(email: str):
    key = email_key(email)

    code_ttl = redis_client.ttl(f"auth:code:{key}")
    cooldown_ttl = redis_client.ttl(
        f"auth:cooldown:{key}"
    )

    now = datetime.now(timezone.utc)

    return {
        "expires_at": now + timedelta(
            seconds=max(code_ttl, 0)
        ),
        "resend_available_at": now + timedelta(
            seconds=max(cooldown_ttl, 0)
        ),
        "server_time": now,
    }


def send_verification_email(email: str, code: str):
    safe_code = html.escape(code)

    html_body = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <body style="
        font-family:Arial,sans-serif;
        background:#f5f7fb;
        padding:32px;
    ">
      <div style="
          max-width:480px;
          margin:auto;
          padding:32px;
          background:white;
          border-radius:12px;
      ">
        <h2 style="color:#1677ff;">
          Movie Recommender
        </h2>

        <p>이메일 인증번호를 안내드립니다.</p>

        <div style="
            text-align:center;
            font-size:36px;
            font-weight:bold;
            letter-spacing:8px;
            padding:24px;
            background:#f0f5ff;
            border-radius:8px;
        ">
          {safe_code}
        </div>

        <p>인증번호는 5분 동안 유효합니다.</p>
        <p>본인이 요청하지 않았다면 무시해 주세요.</p>
      </div>
    </body>
    </html>
    """

    msg = EmailMessage()
    msg["Subject"] = "[Movie Recommender] 이메일 인증번호"
    msg["From"] = settings.GMAIL_ADDRESS
    msg["To"] = email

    msg.set_content(
        f"이메일 인증번호: {code}\n유효 시간: 5분"
    )

    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        timeout=15,
    ) as smtp:
        smtp.login(
            settings.GMAIL_ADDRESS,
            settings.GMAIL_APP_PASSWORD,
        )
        smtp.send_message(msg)