# tests/unit/test_user_schemas.py

import pytest
from pydantic import ValidationError

from app.schemas.user import UserUpdate, PasswordUpdate


# ---------------------------------------------
# Unit Tests for the UserUpdate Schema
# ---------------------------------------------

def test_user_update_allows_all_fields_omitted():
    """A UserUpdate with no fields set should be valid (partial update)."""
    update = UserUpdate()
    assert update.model_dump(exclude_unset=True) == {}


def test_user_update_allows_partial_update():
    """Only the fields actually provided should appear in exclude_unset output."""
    update = UserUpdate(first_name="Jane")
    assert update.model_dump(exclude_unset=True) == {"first_name": "Jane"}


def test_user_update_rejects_invalid_email():
    with pytest.raises(ValidationError):
        UserUpdate(email="not-an-email")


def test_user_update_rejects_short_username():
    with pytest.raises(ValidationError):
        UserUpdate(username="ab")


def test_user_update_accepts_valid_full_update():
    update = UserUpdate(
        username="newname",
        email="new@example.com",
        first_name="New",
        last_name="Name",
    )
    assert update.model_dump(exclude_unset=True) == {
        "username": "newname",
        "email": "new@example.com",
        "first_name": "New",
        "last_name": "Name",
    }


# ---------------------------------------------
# Unit Tests for the PasswordUpdate Schema
# ---------------------------------------------

def test_password_update_accepts_valid_change():
    update = PasswordUpdate(
        current_password="OldPass123!",
        new_password="NewPass123!",
        confirm_new_password="NewPass123!",
    )
    assert update.new_password == "NewPass123!"


def test_password_update_rejects_mismatched_confirmation():
    with pytest.raises(ValidationError, match="do not match"):
        PasswordUpdate(
            current_password="OldPass123!",
            new_password="NewPass123!",
            confirm_new_password="Different123!",
        )


def test_password_update_rejects_reusing_current_password():
    with pytest.raises(ValidationError, match="must be different"):
        PasswordUpdate(
            current_password="SamePass123!",
            new_password="SamePass123!",
            confirm_new_password="SamePass123!",
        )


def test_password_update_rejects_short_new_password():
    with pytest.raises(ValidationError):
        PasswordUpdate(
            current_password="OldPass123!",
            new_password="short",
            confirm_new_password="short",
        )
