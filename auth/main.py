# hack to add project directory to path and make modules work nicely
import sys
from pathlib import Path

PROJECTS_DIR = Path(__file__).resolve().parents[2]
print("Appending PROJECTS_DIR to PATH:", PROJECTS_DIR)
sys.path.append(str(PROJECTS_DIR))

from datetime import timedelta

import toml
from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.auth.dependencies import (
    Token,
    create_access_token,
    get_password_hash,
    authenticate_user,
    create_student,
    # create_admin,
    get_current_student,
    get_current_admin,
    ACCESS_TOKEN_EXPIRE_MIN,
)
from backend.auth.db.main import (
    connect_to_db,
    add_user,
    get_user_by_email,
    update_email_by_id,
    update_password_by_id,
    update_disabled_by_id,
)
from backend.auth.db.models.users import User, UserInDB, UserUpdate

# get the config file path
CONFIG_PATH = Path(__file__).resolve().parent.joinpath("db-config.toml")
print("Using CONFIG_PATH:", CONFIG_PATH)

config = toml.load(str(CONFIG_PATH))


app = FastAPI()

# TODO: make a list of origins, for now the server allows requests from everywhere
# possible a origin_regex could be used instead which matches anything that starts with
# localhost
# origin_regex = "https?://localhost
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def create_dummy_users():
    users = [
        {"email": "luna@google.com", "hashed_password": get_password_hash("luna")},
        {"email": "harley@google.com", "hashed_password": get_password_hash("harley")},
    ]
    for user in users:
        await add_user(UserInDB(**user))
        await add_user(UserInDB(**user))


@app.on_event("startup")
async def startup():
    """
    Connects to the Auth DB using Motor
    """
    db_username = config["atlas-username"]
    db_password = config["atlas-password"]
    db_uri = config["connection-uri"]
    auth_db = config["auth-db"]
    connect_to_db(
        db_uri.format(username=db_username, password=db_password, database=auth_db)
    )


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm does not have an email field, only username
    user = await get_user_by_email(form_data.username)
    if user:
        if user.disabled:
            raise HTTPException(status_code=400, detail="Account is disabled")
        user = authenticate_user(user, form_data.password)

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MIN)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Student GET endpoints
@app.get("/student/me", response_model=User)
async def student_me(current_user: User = Depends(get_current_student)):
    return current_user


@app.get("/student/me/item/")
async def read_own_items(current_user: User = Depends(get_current_student)):
    return [{"data": "junk", "owner": current_user.email}]


# Student POST endpoints
@app.post("/student/register")
async def register(user: User = Depends(create_student)):
    return user


# Student PUT endpoints
@app.put("/student/update_email", response_model=User)
async def update_email(
    current_user: User = Depends(get_current_student), updates: UserUpdate = Body(...)
):

    if not updates.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required",
        )

    existing_user = await get_user_by_email(updates.email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That email is already taken",
        )

    return await update_email_by_id(current_user.id, updates.email)


@app.put("/student/update_password", response_model=User)
async def update_password(
    current_user: User = Depends(get_current_student), updates: UserUpdate = Body(...)
):
    if not updates.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required",
        )
    if not len(updates.password) >= 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must have six characters",
        )

    hashed_password = get_password_hash(updates.password)

    return await update_password_by_id(current_user.id, hashed_password)


# NOTE: Disabling cannot currently be undone by the student
@app.put("/student/update_disabled", response_model=User)
async def update_disabled(
    current_user: User = Depends(get_current_student), updates: UserUpdate = Body(...)
):
    if not updates.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disabled is required",
        )

    return await update_disabled_by_id(current_user.id, updates.disabled)


# Admin GET endpoints
@app.get("/admin/me", response_model=User)
async def admin_me(current_user: User = Depends(get_current_admin)):
    return current_user


# Admin POST endpoints
# This is commented out so that new admins cannot easily be created
# @app.post("/admin/register")
# async def register(user: User = Depends(create_admin)):
#     return user

# TODO: Add Admin PUT endpoints that allow modifying student accounts

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
