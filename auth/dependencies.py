from pathlib import Path

from datetime import datetime, timedelta
from typing import Optional

import toml
import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, UUID4

from backend.auth.db.models.users import UserInDB, UserCreate, User, UserRole

from backend.auth.db.main import get_user_by_email, add_user, get_user_by_id

# get the config file path
CONFIG_PATH = Path(__file__).resolve().parent.joinpath("db-config.toml")
print("Using CONFIG_PATH:", CONFIG_PATH)
config = toml.load(str(CONFIG_PATH))
SECRET_KEY = config["secret"]

# aws s3 config stuff
AWS_CONFIG_PATH = Path(__file__).resolve().parent.joinpath("aws-config.toml")
if AWS_CONFIG_PATH.exists():
    aws_config = toml.load(str(AWS_CONFIG_PATH))
    AWS_ACCESS_KEY_ID = aws_config["aws-access-key-id"]
    AWS_SECRET_ACCESS_KEY = aws_config["aws-secret-access-key"]
    AWS_BUCKET_NAME = aws_config["aws-bucket-name"]

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MIN = 240


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: UUID4
    role: UserRole


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(user: UserInDB, password: str):
    if not verify_password(password, user.hashed_password):
        return False
    return user


# s3 presigned url helpers
# based on "https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html"
def create_presigned_url(object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": AWS_BUCKET_NAME, "Key": object_name},
            ExpiresIn=expiration,
        )
    except ClientError as e:
        print("ERROR:", e)
        return None

    # The response contains the presigned URL
    return response


# based on "https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html"
def create_presigned_post(object_name, fields=None, conditions=None, expiration=3600):
    """Generate a presigned URL S3 POST request to upload a file

    :param object_name: string
    :param fields: Dictionary of prefilled form fields
    :param conditions: List of conditions to include in the policy
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Dictionary with the following keys:
        url: URL to post to
        fields: Dictionary of form fields and values to submit with the POST
    :return: None if error.
    """

    # Generate a presigned S3 POST URL
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    try:
        response = s3_client.generate_presigned_post(
            AWS_BUCKET_NAME,
            object_name,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expiration,
        )
    except ClientError as e:
        print("ERROR:", e)
        return None

    # The response contains the presigned URL and required fields
    return response


async def create_user(user: UserCreate) -> User:
    """
    Accepts a UserCreate model and returns a User
    This is endpoint allows both users of any role to be created.
    It should only be used for testing
    """

    existing_user = await get_user_by_email(user.email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    hashed_password = get_password_hash(user.password)
    db_user = UserInDB(**user.dict(), hashed_password=hashed_password)

    await add_user(db_user)
    return User(**user.dict())


async def create_student(user: UserCreate) -> User:
    """
    Accepts a UserCreate model which has role set as student and returns a User
    """

    existing_user = await get_user_by_email(user.email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    if user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect role, expected student",
        )

    hashed_password = get_password_hash(user.password)
    db_user = UserInDB(**user.dict(), hashed_password=hashed_password)

    await add_user(db_user)
    return User(**user.dict())


async def create_admin(user: UserCreate) -> User:
    """
    Accepts a UserCreate model which has role set as admin and returns a User
    """

    existing_user = await get_user_by_email(user.email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect role, expected student",
        )

    hashed_password = get_password_hash(user.password)
    db_user = UserInDB(**user.dict(), hashed_password=hashed_password)

    await add_user(db_user)
    return User(**user.dict())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MIN)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_token_data(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uuid = payload.get("sub")
        if uuid is None:
            raise credentials_exception
        role = payload.get("role")
        token_data = TokenData(id=UUID4(uuid), role=role)
    except JWTError:
        raise credentials_exception

    return token_data


async def get_student_token_data(
    token_data: TokenData = Depends(get_current_token_data),
):
    role_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate role",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token_data.role != UserRole.student:
        raise role_exception

    return token_data


async def get_admin_token_data(token_data: TokenData = Depends(get_current_token_data)):
    role_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate role",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token_data.role != UserRole.admin:
        raise role_exception

    return token_data


async def get_current_user(token_data: TokenData = Depends(get_current_token_data)):
    """
    Uses dependency injection to authenticate `token_data`, and returns a User
    """

    user = await get_user_by_id(id=token_data.id)
    # I don't think this should ever happen
    if not user:
        print("BIG PROBLEM, USER NOT FOUND BUT TOKEN AUTHENTICATED")
        assert 1 == 0
    if user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


async def get_current_student(token_data: TokenData = Depends(get_student_token_data)):
    """
    Uses dependency injection to authenticate `token_data` and ensure `role` is set to
    student.
    Then, returns a User
    """
    user = await get_user_by_id(id=token_data.id)
    # I don't think this should ever happen
    if not user:
        print("BIG PROBLEM, USER NOT FOUND BUT TOKEN AUTHENTICATED")
        assert 1 == 0
    if user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


async def get_current_admin(token_data: TokenData = Depends(get_admin_token_data)):
    """
    Uses dependency injection to authenticate `token_data` and ensure `role` is set to
    admin.
    Then, returns a User
    """
    user = await get_user_by_id(id=token_data.id)
    # I don't think this should ever happen
    if not user:
        print("BIG PROBLEM, USER NOT FOUND BUT TOKEN AUTHENTICATED")
        assert 1 == 0
    if user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
