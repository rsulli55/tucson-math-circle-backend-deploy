from typing import Optional
from pydantic import Field, EmailStr
from backend.main.db.mixins import IdMixin


class AdminProfileModel(IdMixin):
    email: Optional[EmailStr] = Field()
    phone_number: Optional[str] = Field()
    first_name: str = Field()
    last_name: str = Field()
    username: str = Field()
    section_access: list = Field()
