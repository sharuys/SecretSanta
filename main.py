from fastapi import FastAPI, HTTPException, status, Query

app = FastAPI(title="Secret Nick API")

fake_rooms_db = {
    10: {"name": "Кімната 1 (Відкрита)", "is_closed": False},
    20: {"name": "Кімната 2 (Закрита)", "is_closed": True},
}

fake_users_db = {
    1: {"id": 1, "user_code": "admin_10", "role": "admin", "room_id": 10},
    2: {"id": 2, "user_code": "member_A", "role": "member", "room_id": 10},
    3: {"id": 3, "user_code": "member_B", "role": "member", "room_id": 10},

    4: {"id": 4, "user_code": "admin_20", "role": "admin", "room_id": 20},
    5: {"id": 5, "user_code": "member_C", "role": "member", "room_id": 20},
}

def find_user_by_id(user_id: int):
    return fake_users_db.get(user_id)


def find_user_by_code(user_code: str):
    for user in fake_users_db.values():
        if user["user_code"] == user_code:
            return user
    return None


def find_room_by_id(room_id: int):
    return fake_rooms_db.get(room_id)



@app.delete("/users/{id}")
async def delete_user(id: int, userCode: str = Query(..., min_length=1)):
    """
    Видаляє користувача з кімнати.
    - id: ID користувача, якого видаляють.
    - userCode: Унікальний код адміністратора, який виконує дію.
    """
    user_to_delete = find_user_by_id(id)
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Користувача з id {id} не знайдено"
        )

    admin_user = find_user_by_code(userCode)
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Користувача з userCode {userCode} не знайдено"
        )

    if admin_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Користувач з userCode не є адміністратором"
        )

    if admin_user["room_id"] != user_to_delete["room_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Користувач та адміністратор належать до різних кімнат"
        )

    if admin_user["id"] == user_to_delete["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Адміністратор не може видалити сам себе"
        )

    room = find_room_by_id(admin_user["room_id"])
    if not room or room["is_closed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Кімната вже закрита для змін"
        )

    try:

        if id in fake_users_db:
            del fake_users_db[id]
        else:
            return {"status": "success", "message": f"User {id} already deleted"}

        return {"status": "success", "message": f"User {id} deleted", "deleted_user": user_to_delete}

    except KeyError:
        raise HTTPException(status_code=500, detail="Помилка видалення користувача")
