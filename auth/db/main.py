import motor.motor_asyncio
from pydantic import UUID4, EmailStr


from backend.auth.db.models.users import UserInDB

client: motor.motor_asyncio.AsyncIOMotorClient
database: motor.motor_asyncio.AsyncIOMotorDatabase
users_collection: motor.motor_asyncio.AsyncIOMotorCollection


def connect_to_db(uri: str):
    global client
    global database
    global users_collection
    client = motor.motor_asyncio.AsyncIOMotorClient(uri, uuidRepresentation="standard")
    database = client.auth_db
    users_collection = database.users


async def add_user(user: UserInDB):
    await users_collection.insert_one(user.dict())


async def get_user_by_id(id: UUID4):
    user = await users_collection.find_one({"id": id})
    # TODO: not sure about error handling here
    if user:
        return UserInDB(**user)
    return False


async def get_user_by_email(email: EmailStr):
    user = await users_collection.find_one({"email": email})
    # TODO: not sure about error handling here
    if user:
        return UserInDB(**user)
    return False


async def update_email_by_id(id: UUID4, new_email: EmailStr):
    await users_collection.update_one({"id": id}, {"$set": {"email": new_email}})
    updated_user = await get_user_by_id(id)
    return updated_user


async def update_password_by_id(id: UUID4, new_hashed_pass: str):
    await users_collection.update_one(
        {"id": id}, {"$set": {"hashed_password": new_hashed_pass}}
    )
    updated_user = await get_user_by_id(id)
    return updated_user


async def update_disabled_by_id(id: UUID4, new_disabled: bool):
    await users_collection.update_one({"id": id}, {"$set": {"disabled": new_disabled}})
    updated_user = await get_user_by_id(id)
    return updated_user
