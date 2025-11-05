import pytest
from fastapi.testclient import TestClient
from main import app, fake_users_db, fake_rooms_db

original_users_db = {}
original_rooms_db = {}


@pytest.fixture(autouse=True)
def reset_db_state():
    global original_users_db, original_rooms_db

    if not original_users_db:
        original_users_db = fake_users_db.copy()
        original_rooms_db = fake_rooms_db.copy()

    fake_users_db.clear()
    fake_users_db.update(original_users_db.copy())

    fake_rooms_db.clear()
    fake_rooms_db.update(original_rooms_db.copy())

    yield


client = TestClient(app)

def test_delete_user_success(reset_db_state):
    """1. Позитивний сценарій: Адмін (admin_10) видаляє учасника (member_A)"""
    user_id_to_delete = 2
    admin_code = "admin_10"

    response = client.delete(f"/users/{user_id_to_delete}?userCode={admin_code}")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["deleted_user"]["id"] == user_id_to_delete
    assert user_id_to_delete not in fake_users_db  # Переконуємось, що він зник


def test_fail_user_not_found(reset_db_state):
    """2. Користувача з id не знайдено"""
    response = client.delete("/users/999?userCode=admin_10")
    assert response.status_code == 404
    assert "Користувача з id 999 не знайдено" in response.json()["detail"]


def test_fail_admin_code_not_found(reset_db_state):
    """3. Користувача з userCode не знайдено"""
    response = client.delete("/users/3?userCode=bad_admin_code")
    assert response.status_code == 404
    assert "Користувача з userCode bad_admin_code не знайдено" in response.json()["detail"]


def test_fail_user_not_admin(reset_db_state):
    """4. Користувач з userCode не адміністратор (пробуємо видалити учасником)"""
    response = client.delete("/users/3?userCode=member_B")
    assert response.status_code == 403
    assert "не є адміністратором" in response.json()["detail"]


def test_fail_different_rooms(reset_db_state):
    """5. Користувач з userCode і id належать до різних кімнат"""
    # Адмін admin_10 (кімната 10) пробує видалити member_C (кімната 20)
    response = client.delete("/users/5?userCode=admin_10")
    assert response.status_code == 400
    assert "належать до різних кімнат" in response.json()["detail"]


def test_fail_admin_deletes_self(reset_db_state):
    """6. Користувач з userCode і id це один і той самий користувач"""
    response = client.delete("/users/1?userCode=admin_10")
    assert response.status_code == 400
    assert "Адміністратор не може видалити сам себе" in response.json()["detail"]


def test_fail_room_is_closed(reset_db_state):
    """7. Кімната вже закрита (використовуємо дані кімнати 20)"""
    response = client.delete("/users/5?userCode=admin_20")
    assert response.status_code == 400
    assert "Кімната вже закрита" in response.json()["detail"]