# hack to add project directory to path and make modules work nicely
import sys
from pathlib import Path

PROJECTS_DIR = Path(__file__).resolve().parents[3]
print("Appending PROJECTS_DIR to PATH:", PROJECTS_DIR)
sys.path.append(str(PROJECTS_DIR))
# end hack

from datetime import timedelta

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# main db imports
from backend.main.src.routers import student, admin
from backend.connect_to_mongodb import connect_to_mongodb, connect_to_auth_db
from backend.main.db.mixins import PresignedPostUrlInfo

# auth db imports
from backend.auth.dependencies import (
    Token,
    TokenData,
    create_access_token,
    authenticate_user,
    ACCESS_TOKEN_EXPIRE_MIN,
    create_presigned_post,
    get_current_token_data,
)
from backend.auth.db.main import get_user_by_email

# flag which controls whether a connection to the auth_db is opened
TESTING = True

app = FastAPI()


app.include_router(student.router, prefix="/student", tags=["Students"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

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


# These two functions are here to make the Authorize button work on FastAPI docs
@app.on_event("startup")
async def startup():
    if TESTING:
        connect_to_auth_db()


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm does not have an email field, only username
    user = await get_user_by_email(form_data.username)
    if user:
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


@app.post("/presigned_url_for_upload")
async def generate_presigned_post_url(
    info: PresignedPostUrlInfo, token_data: TokenData = Depends(get_current_token_data)
):
    response = create_presigned_post(info.object_name, info.fields, info.conditions)

    if response is not None:
        return response

    return {"details": "Could not generate presigned url"}


if __name__ == "__main__":
    connect_to_mongodb()
    uvicorn.run(app, host="127.0.0.1", port=9000)
