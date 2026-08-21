from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.exceptions import NotAllowed
from app.core.security import decode_access_token
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login/form")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    from app.core.exceptions import InvalidCredentials

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise InvalidCredentials("Токен недействителен")
    user = await db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise InvalidCredentials("Пользователь не найден")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise NotAllowed("Требуются права администратора")
    return user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]
