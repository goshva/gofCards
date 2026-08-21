from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.exceptions import AlreadyExists, InvalidCredentials
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.user import RegisterResult, Token, UserCreate, UserLogin, UserOut
from app.services.quest_service import QuestService
from typing import Annotated
from fastapi import Depends

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_for(user: User) -> Token:
    return Token(
        access_token=create_access_token(user.id, {"role": user.role.value}),
        user=UserOut.model_validate(user),
    )


async def _authenticate(db: DbSession, username: str, password: str) -> User:
    user = await db.scalar(
        select(User).where(or_(User.username == username, User.email == username.lower()))
    )
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentials()
    if not user.is_active:
        raise InvalidCredentials("Аккаунт отключён")
    return user


@router.post("/register", response_model=RegisterResult, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: DbSession) -> RegisterResult:
    exists = await db.scalar(
        select(User).where(
            or_(User.username == payload.username, User.email == payload.email.lower())
        )
    )
    if exists is not None:
        raise AlreadyExists("Пользователь с таким именем или email уже существует")

    user = User(
        username=payload.username,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        coins=settings.starting_coins,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    quests = QuestService(db)
    await quests.ensure_code(user)
    referral = await quests.register_referral(user, payload.referral_code or "")

    # no free squad: players are bought with the starting coins
    return RegisterResult(
        token=_token_for(user),
        welcome_cards=0,
        referral_bonus=referral.invitee_reward if referral else 0,
    )


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, db: DbSession) -> Token:
    return _token_for(await _authenticate(db, payload.username, payload.password))


@router.post("/login/form", response_model=Token, include_in_schema=False)
async def login_form(
    db: DbSession, form: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """Kept so the Swagger Authorize button works."""
    return _token_for(await _authenticate(db, form.username, form.password))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
