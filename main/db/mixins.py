from enum import Enum
from typing import Any, Optional, Dict, List

from pydantic import BaseModel, Field, validator, BaseConfig
from bson.objectid import ObjectId, InvalidId


class SessionLevel(str, Enum):
    junior_a = "junior_a"
    junior_b = "junior_b"
    senior = "senior"


class PydanticObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        try:
            ObjectId(str(v))
        except InvalidId:
            raise ValueError("Not a valid ObjectId")
        return str(v)

    class Config(BaseConfig):
        json_encoders = {
            ObjectId: lambda oid: str(oid),
        }


class PresignedPostUrlInfo(BaseModel):
    fields: Optional[Dict[str, str]] = Field(None, title="This is optional")
    conditions: Optional[List] = Field(None, title="This is optional")
    object_name: str


class IdMixin(BaseModel):
    id: Optional[Any] = Field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.id == "None":
            self.id = None

    @validator("id")
    def validate_id(cls, id):
        return str(id)
