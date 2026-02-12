"""Django integration for EasyGoogleAPI.

Provides a Django-ORM-backed token store so that OAuth tokens can be
persisted in your project's database without any extra infrastructure.

Usage::

    # models.py
    from django.db import models

    class OAuthToken(models.Model):
        user_id  = models.CharField(max_length=255, unique=True)
        token_data = models.JSONField()

    # views.py
    from easygoogleapi.contrib.django import DjangoModelTokenStore
    from .models import OAuthToken

    store = DjangoModelTokenStore(
        model=OAuthToken,
        user_id_field="user_id",
        token_data_field="token_data",
    )
"""

from __future__ import annotations

from typing import Any


class DjangoModelTokenStore:
    """Token store backed by a Django Model.

    This class implements the ``TokenStore`` protocol using the Django ORM.
    It does **not** import Django at module level so the library can be
    installed without Django present — the import is deferred to the
    constructor.

    Args:
        model: The Django Model class used to store tokens.  The model
            must have at least two fields: one for the user identifier
            (``CharField`` / ``TextField``) and one for the serialized
            token data (``JSONField``).
        user_id_field: Name of the model field that stores the user ID
            (default ``"user_id"``).
        token_data_field: Name of the model field that stores the token
            data dict (default ``"token_data"``).
    """

    def __init__(
        self,
        model: Any,
        user_id_field: str = "user_id",
        token_data_field: str = "token_data",
    ) -> None:
        self._model = model
        self._user_id_field = user_id_field
        self._token_data_field = token_data_field

    # -- TokenStore protocol -------------------------------------------------

    def get(self, user_id: str) -> dict[str, Any] | None:
        """Retrieve token data for *user_id*, or ``None``."""
        try:
            obj = self._model.objects.get(**{self._user_id_field: user_id})
            return getattr(obj, self._token_data_field)
        except self._model.DoesNotExist:
            return None

    def save(self, user_id: str, token_data: dict[str, Any]) -> None:
        """Create or update the token row for *user_id*."""
        self._model.objects.update_or_create(
            defaults={self._token_data_field: token_data},
            **{self._user_id_field: user_id},
        )

    def delete(self, user_id: str) -> bool:
        """Delete the token row for *user_id*. Returns ``True`` if deleted."""
        deleted_count, _ = self._model.objects.filter(
            **{self._user_id_field: user_id}
        ).delete()
        return deleted_count > 0
