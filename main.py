from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware  # Додано для фронтенду
from pydantic import BaseModel, Field
import uuid
import random

# --- Моделі Pydantic (для валідації) ---
class GifteeResponse(BaseModel):
    your_name: str
    giftee_name: str
    giftee_wishlist: str
    room_budget: str

class RoomCreateRequest(BaseModel):
    room_name: str = Field(..., min_length=3, max_length=50)
    admin_name: str = Field(..., min_length=3, max_length=30)
    budget: str | None = Field(default="Не вказано", max_length=50)
    wishlist: str | None = Field(default="Не вказано", max_length=200)

class RoomCreateResponse(BaseModel):
    """
    ОНОВЛЕНА МОДЕЛЬ ВІДПОВІДІ
    Повертаємо тільки коди, а фронтенд сам збудує посилання
    """
    room_id: int
    member_join_code: str
    admin_user_code: str

class UserJoinRequest(BaseModel):
    user_name: str = Field(..., min_length=3, max_length=30)
    wishlist: str | None = Field(default="Сюрприз!", max_length=200)

class UserJoinResponse(BaseModel):
    user_id: int
    user_code: str
    room_name: str
    message: str

class RandomizeResponse(BaseModel):
    status: str
    message: str
    pairs_count: int

# --- Ініціалізація FastAPI та CORS ---

app = FastAPI(title="Secret Nick API")

# -----------------------------------------------
# ⬇️⬇️⬇️ ОНОВЛЕНИЙ БЛОК CORS ⬇️⬇️⬇️
# -----------------------------------------------
# Дозволяємо доступ з будь-якого домену ("*")
# Це найпростіший шлях для деплойменту
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -----------------------------------------------
# ⬆️⬆️⬆️ КІНЕЦЬ БЛОКУ ⬆️⬆️⬆️
# -----------------------------------------------


# --- Наша "фальшива" База Даних ---

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


# --- Допоміжні функції ---
def find_room_by_join_code(join_code: str):
    for room_id, room_details in fake_rooms_db.items():
        if room_details.get("member_join_code") == join_code:
            return room_id, room_details
    return None, None

def get_new_room_id():
    if not fake_rooms_db:
        return 1
    return max(fake_rooms_db.keys()) + 1

def get_new_user_id():
    if not fake_users_db:
        return 1
    return max(fake_users_db.keys()) + 1

def find_user_by_id(user_id: int):
    return fake_users_db.get(user_id)

def find_user_by_code(user_code: str):
    for user in fake_users_db.values():
        if user["user_code"] == user_code:
            return user
    return None

def find_room_by_id(room_id: int):
    return fake_rooms_db.get(room_id)

def get_users_by_room_id(room_id: int):
    return [user for user in fake_users_db.values() if user["room_id"] == room_id]


# --- Ендпоінти API ---
@app.get("/users/me", response_model=GifteeResponse)
async def get_my_giftee(userCode: str = Query(..., min_length=1)):
    # ... (код без змін) ...
    user = find_user_by_code(userCode)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Користувача з таким кодом не знайдено.")
    room = find_room_by_id(user["room_id"])
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кімнату, до якої належить користувач, не знайдено.")
    if not room["is_closed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Гра ще не почалася! Адміністратор ще не запустив жеребкування.")
    giftee_id = user.get("giftee_id")
    if not giftee_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Помилка: Жеребкування відбулося, але вам не призначено пару. Зверніться до адміна.")
    giftee = find_user_by_id(giftee_id)
    if not giftee:
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Помилка: Вашу пару було видалено з гри. Зверніться до адміна.")
    return {
        "your_name": user["name"],
        "giftee_name": giftee["name"],
        "giftee_wishlist": giftee.get("wishlist", "Не вказано"),
        "room_budget": room.get("budget", "Не вказано")
    }

@app.post("/rooms/{room_id}/start", response_model=RandomizeResponse)
async def start_game_and_randomize(room_id: int, userCode: str = Query(..., min_length=1)):
    # ... (код без змін) ...
    admin_user = find_user_by_code(userCode)
    if not admin_user or admin_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Тільки адміністратор може запустити гру.")
    room = find_room_by_id(room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кімнату не знайдено.")
    if admin_user["room_id"] != room_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Адміністратор не належить до цієї кімнати.")
    if room["is_closed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Гра в цій кімнаті вже запущена. Зміни неможливі.")
    room_users = get_users_by_room_id(room_id)
    if len(room_users) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для запуску гри потрібно щонайменше 3 учасники.")
    user_ids = [user["id"] for user in room_users]
    random.shuffle(user_ids)
    receivers = user_ids[1:] + user_ids[:1]
    pairs_count = 0
    for giver_id, receiver_id in zip(user_ids, receivers):
        fake_users_db[giver_id]["giftee_id"] = receiver_id
        pairs_count += 1
    room["is_closed"] = True
    return {"status": "success", "message": "Гра успішно запущена! Пари розподілено.", "pairs_count": pairs_count}

@app.post("/rooms/join/", response_model=UserJoinResponse, status_code=status.HTTP_201_CREATED)
async def join_room(join_code: str, user_data: UserJoinRequest):
    # ... (код без змін) ...
    room_id, room = find_room_by_join_code(join_code)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кімнату з таким кодом для приєднання не знайдено.")
    if room["is_closed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Набір у цю кімнату вже закрито.")
    new_user_id = get_new_user_id()
    new_user_code = f"member_{uuid.uuid4().hex[:8]}"
    new_user = {
        "id": new_user_id,
        "user_code": new_user_code,
        "role": "member",
        "room_id": room_id,
        "name": user_data.user_name,
        "wishlist": user_data.wishlist
    }
    fake_users_db[new_user_id] = new_user
    return {
        "user_id": new_user_id,
        "user_code": new_user_code,
        "room_name": room["name"],
        "message": f"Ви успішно приєдналися до кімнати '{room['name']}'!"
    }

@app.post("/rooms/", response_model=RoomCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_room(room_data: RoomCreateRequest):
    """
    ОНОВЛЕНИЙ ЕНДПОІНТ
    Створює кімнату та повертає коди
    """
    # 1. Генеруємо унікальні ID та коди
    new_room_id = get_new_room_id()
    new_admin_id = get_new_user_id()
    admin_code = f"admin_{uuid.uuid4().hex[:8]}"
    member_join_code = f"join_{uuid.uuid4().hex[:6]}"

    # 2. Створюємо нову кімнату
    new_room = {
        "name": room_data.room_name,
        "is_closed": False,
        "budget": room_data.budget,
        "member_join_code": member_join_code
    }
    fake_rooms_db[new_room_id] = new_room

    # 3. Створюємо користувача-адміністратора
    new_admin = {
        "id": new_admin_id,
        "user_code": admin_code,
        "role": "admin",
        "room_id": new_room_id,
        "name": room_data.admin_name,
        "wishlist": room_data.wishlist
    }
    fake_users_db[new_admin_id] = new_admin

    # 4. Повертаємо коди
    return {
        "room_id": new_room_id,
        "member_join_code": member_join_code,
        "admin_user_code": admin_code
    }


@app.delete("/users/{id}")
async def delete_user(id: int, userCode: str = Query(..., min_length=1)):
    # ... (код без змін) ...
    user_to_delete = find_user_by_id(id)
    if not user_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Користувача з id {id} не знайдено")
    admin_user = find_user_by_code(userCode)
    if not admin_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Користувача з userCode {userCode} не знайдено")
    if admin_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Користувач з userCode не є адміністратором")
    if admin_user["room_id"] != user_to_delete["room_id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Користувач та адміністратор належать до різних кімнат")
    if admin_user["id"] == user_to_delete["id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Адміністратор не може покинути кімнату (тільки видалити її)")
    room = find_room_by_id(admin_user["room_id"])
    if not room or room["is_closed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Кімната вже закрита для змін")
    try:
        if id in fake_users_db:
            del fake_users_db[id]
        else:
            return {"status": "success", "message": f"User {id} already deleted"}
        return {"status": "success", "message": f"User {id} deleted", "deleted_user": user_to_delete}
    except KeyError:
        raise HTTPException(status_code=500, detail="Внутрішня помилка сервера при видаленні")