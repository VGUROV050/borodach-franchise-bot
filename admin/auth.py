# Admin authentication

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config.settings import ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_SECRET_KEY

security = HTTPBasic()

# Простое хранилище сессий (в памяти)
# В продакшене лучше использовать Redis
sessions: dict[str, datetime] = {}

SESSION_LIFETIME = timedelta(hours=24)


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


def create_session(username: str) -> str:
    """Создать сессию."""
    token = secrets.token_urlsafe(32)
    sessions[token] = datetime.now() + SESSION_LIFETIME
    return token


def verify_session(request: Request) -> Optional[str]:
    """Проверить сессию из cookie."""
    token = request.cookies.get("session_token")
    
    if not token:
        return None
    
    expiry = sessions.get(token)
    if not expiry or datetime.now() > expiry:
        # Сессия истекла
        sessions.pop(token, None)
        return None
    
    return token


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

