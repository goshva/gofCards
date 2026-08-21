from __future__ import annotations

from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base for domain errors so handlers can stay thin."""

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Application error"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(status_code=self.status_code, detail=detail or self.detail)


class InsufficientFunds(AppError):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    detail = "Недостаточно монет"


class NotOwner(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Карточка не принадлежит пользователю"


class NotAllowed(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Действие запрещено"


class NotFound(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Не найдено"


class CardLocked(AppError):
    status_code = status.HTTP_409_CONFLICT
    detail = "Карточка участвует в активном предложении обмена"


class InvalidSquad(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Состав невалиден"


class SquadLocked(AppError):
    status_code = status.HTTP_409_CONFLICT
    detail = "Состав на этот матч уже закрыт"


class AlreadyExists(AppError):
    status_code = status.HTTP_409_CONFLICT
    detail = "Уже существует"


class InvalidCredentials(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Неверный логин или пароль"
