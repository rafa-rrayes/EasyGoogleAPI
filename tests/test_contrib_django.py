"""Tests for DjangoModelTokenStore with a mock Django model."""

from unittest.mock import MagicMock

import pytest

from easygoogleapi.contrib.django import DjangoModelTokenStore


class FakeDoesNotExist(Exception):
    """Simulates Django Model.DoesNotExist."""
    pass


def _make_mock_model():
    """Create a mock Django model class with .objects manager."""
    model = MagicMock()
    model.DoesNotExist = FakeDoesNotExist
    return model


class TestDjangoModelTokenStore:
    """Unit tests for DjangoModelTokenStore."""

    def test_get_returns_token_data(self):
        model = _make_mock_model()
        obj = MagicMock()
        obj.token_data = {"token": "abc", "refresh_token": "xyz"}
        model.objects.get.return_value = obj

        store = DjangoModelTokenStore(model)
        result = store.get("user_1")

        model.objects.get.assert_called_once_with(user_id="user_1")
        assert result == {"token": "abc", "refresh_token": "xyz"}

    def test_get_returns_none_when_not_found(self):
        model = _make_mock_model()
        model.objects.get.side_effect = FakeDoesNotExist

        store = DjangoModelTokenStore(model)
        result = store.get("missing_user")
        assert result is None

    def test_save_calls_update_or_create(self):
        model = _make_mock_model()
        store = DjangoModelTokenStore(model)

        token_data = {"token": "new_token"}
        store.save("user_2", token_data)

        model.objects.update_or_create.assert_called_once_with(
            defaults={"token_data": token_data},
            user_id="user_2",
        )

    def test_delete_returns_true_when_deleted(self):
        model = _make_mock_model()
        model.objects.filter().delete.return_value = (1, {})

        store = DjangoModelTokenStore(model)
        assert store.delete("user_3") is True

    def test_delete_returns_false_when_not_found(self):
        model = _make_mock_model()
        model.objects.filter().delete.return_value = (0, {})

        store = DjangoModelTokenStore(model)
        assert store.delete("missing_user") is False

    def test_custom_field_names(self):
        model = _make_mock_model()
        obj = MagicMock()
        obj.data = {"token": "custom"}
        model.objects.get.return_value = obj

        store = DjangoModelTokenStore(
            model,
            user_id_field="uid",
            token_data_field="data",
        )
        result = store.get("u1")

        model.objects.get.assert_called_once_with(uid="u1")
        assert result == {"token": "custom"}

    def test_save_with_custom_field_names(self):
        model = _make_mock_model()
        store = DjangoModelTokenStore(
            model,
            user_id_field="uid",
            token_data_field="data",
        )

        store.save("u2", {"token": "val"})
        model.objects.update_or_create.assert_called_once_with(
            defaults={"data": {"token": "val"}},
            uid="u2",
        )
