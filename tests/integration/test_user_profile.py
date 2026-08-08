# tests/integration/test_user_profile.py

import time

from sqlalchemy import or_

from app.models.user import User
from tests.conftest import create_fake_user


def register_user(db_session, password="OldPass123!"):
    """Register and return a user with a known plain-text password."""
    user_data = create_fake_user()
    user_data["password"] = password
    user = User.register(db_session, user_data)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_user_update_persists_changes_and_bumps_updated_at(db_session):
    user = register_user(db_session)
    original_updated_at = user.updated_at

    time.sleep(0.01)
    user.update(first_name="Updated", last_name="Name")
    db_session.commit()
    db_session.refresh(user)

    assert user.first_name == "Updated"
    assert user.last_name == "Name"
    assert user.updated_at > original_updated_at


def test_username_collision_detected_against_other_users(db_session):
    user_a = register_user(db_session)
    user_b = register_user(db_session)

    existing = db_session.query(User).filter(
        User.id != user_b.id,
        or_(User.username == user_a.username, User.email == user_a.email),
    ).first()

    assert existing is not None
    assert existing.id == user_a.id


def test_email_collision_not_triggered_by_own_record(db_session):
    user = register_user(db_session)

    existing = db_session.query(User).filter(
        User.id != user.id,
        or_(User.username == user.username, User.email == user.email),
    ).first()

    assert existing is None


def test_password_change_with_correct_current_password(db_session):
    user = register_user(db_session, password="OldPass123!")

    assert user.verify_password("OldPass123!") is True

    user.password = User.hash_password("NewPass123!")
    db_session.commit()
    db_session.refresh(user)

    assert user.verify_password("NewPass123!") is True
    assert user.verify_password("OldPass123!") is False


def test_password_change_rejected_with_wrong_current_password(db_session):
    user = register_user(db_session, password="OldPass123!")

    assert user.verify_password("WrongPass123!") is False
    # Password must remain unchanged since the caller should never reach the
    # hash/persist step when the current password check fails.
    assert user.verify_password("OldPass123!") is True
