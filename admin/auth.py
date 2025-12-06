# Admin authentication with security improvements

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

from fastapi import Request, HTTPException, Depends, status
from fastapi.responses import Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config.settings import ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_SECRET_KEY, ENVIRONMENT

security = HTTPBasic()

# ═══════════════════════════════════════════════════════════════════
# Session Storage
# ═══════════════════════════════════════════════════════════════════

# Простое хранилище сессий (в памяти)
# В продакшене лучше использовать Redis
sessions: dict[str, dict] = {}  # token -> {expiry, username, csrf_token}

SESSION_LIFETIME = timedelta(hours=24)

# ═══════════════════════════════════════════════════════════════════
# Brute-force Protection
# ═══════════════════════════════════════════════════════════════════

# Хранилище неудачных попыток: IP -> [timestamps]
_failed_attempts: dict[str, list[datetime]] = defaultdict(list)

# Настройки защиты от brute-force
MAX_FAILED_ATTEMPTS = 5  # Максимум попыток
LOCKOUT_DURATION = timedelta(minutes=15)  # Время блокировки
ATTEMPT_WINDOW = timedelta(minutes=15)  # Окно для подсчёта попыток


def _get_client_ip(request: Request) -> str:
    """Получить IP клиента (учитывая прокси)."""
    # X-Forwarded-For может содержать несколько IP через запятую
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # X-Real-IP от nginx
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback на прямой IP
    return request.client.host if request.client else "unknown"


def _is_locked_out(ip: str) -> bool:
    """Проверить, заблокирован ли IP."""
    now = datetime.now()
    
    # Очищаем старые попытки
    _failed_attempts[ip] = [
        t for t in _failed_attempts[ip]
        if now - t < ATTEMPT_WINDOW
    ]
    
    return len(_failed_attempts[ip]) >= MAX_FAILED_ATTEMPTS


def _record_failed_attempt(ip: str):
    """Записать неудачную попытку входа."""
    _failed_attempts[ip].append(datetime.now())


def _clear_failed_attempts(ip: str):
    """Очистить неудачные попытки после успешного входа."""
    _failed_attempts.pop(ip, None)


def check_brute_force(request: Request):
    """Проверить, не заблокирован ли IP за brute-force."""
    ip = _get_client_ip(request)
    
    if _is_locked_out(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Слишком много неудачных попыток. Попробуйте через {LOCKOUT_DURATION.seconds // 60} минут.",
        )


# ═══════════════════════════════════════════════════════════════════
# CSRF Protection
# ═══════════════════════════════════════════════════════════════════

def generate_csrf_token() -> str:
    """Генерировать CSRF токен."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(request: Request, form_token: Optional[str] = None) -> bool:
    """Проверить CSRF токен."""
    session_token = request.cookies.get("session_token")
    if not session_token or session_token not in sessions:
        return False
    
    expected_csrf = sessions[session_token].get("csrf_token")
    if not expected_csrf:
        return False
    
    # Токен может быть в форме или в заголовке
    actual_csrf = form_token or request.headers.get("X-CSRF-Token")
    
    if not actual_csrf:
        return False
    
    return secrets.compare_digest(expected_csrf, actual_csrf)


def require_csrf(request: Request, csrf_token: str = None) -> bool:
    """Dependency: требовать валидный CSRF токен для POST/PUT/DELETE."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True
    
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недействительный CSRF токен. Обновите страницу.",
        )
    
    return True


# ═══════════════════════════════════════════════════════════════════
# Authentication
# ═══════════════════════════════════════════════════════════════════

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Проверка логина и пароля."""
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username


def create_session(username: str) -> tuple[str, str]:
    """Создать сессию. Возвращает (session_token, csrf_token)."""
    session_token = secrets.token_urlsafe(32)
    csrf_token = generate_csrf_token()
    
    sessions[session_token] = {
        "expiry": datetime.now() + SESSION_LIFETIME,
        "username": username,
        "csrf_token": csrf_token,
    }
    
    return session_token, csrf_token


def verify_session(request: Request) -> Optional[str]:
    """Проверить сессию из cookie."""
    token = request.cookies.get("session_token")
    
    if not token:
        return None
    
    session = sessions.get(token)
    if not session:
        return None
    
    if datetime.now() > session["expiry"]:
        # Сессия истекла
        sessions.pop(token, None)
        return None
    
    return token


def get_csrf_token(request: Request) -> Optional[str]:
    """Получить CSRF токен для текущей сессии."""
    token = request.cookies.get("session_token")
    if not token or token not in sessions:
        return None
    
    return sessions[token].get("csrf_token")


def require_auth(request: Request) -> str:
    """Dependency: требовать авторизацию."""
    token = verify_session(request)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return token


def set_secure_cookie(
    response: Response,
    key: str,
    value: str,
    max_age: int = None,
) -> Response:
    """
    Установить cookie с правильными флагами безопасности.
    
    Флаги:
    - HttpOnly: защита от XSS (JS не может прочитать)
    - Secure: только HTTPS (в production)
    - SameSite: защита от CSRF
    """
    is_production = ENVIRONMENT == "production"
    
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age or int(SESSION_LIFETIME.total_seconds()),
        httponly=True,  # Защита от XSS
        secure=is_production,  # Только HTTPS в production
        samesite="lax",  # Защита от CSRF
        path="/",
    )
    
    return response


def delete_session(token: str):
    """Удалить сессию."""
    sessions.pop(token, None)


