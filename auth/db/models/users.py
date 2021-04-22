from typing import Optional

from uuid import uuid4
from pydantic import BaseModel, Field, EmailStr, UUID4, validator
from enum import Enum


class UserRole(str, Enum):
    student = "student"
    admin = "admin"
    coordinator = "coordinator"


class User(BaseModel):
    id: UUID4 = Field(default_factory=uuid4)
    email: EmailStr
    role: UserRole
    disabled: Optional[bool] = None


class UserCreate(User):
    password: str

    @validator("password")
    def valid_password(cls, v: str):
        if len(v) < 6:
            raise ValueError("Password should be at least 6 characters")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr]
    password: Optional[str]
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str

    class Config:
        orm_mode = True
