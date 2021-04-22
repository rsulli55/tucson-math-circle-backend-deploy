from typing import Optional, List
from datetime import datetime, date
from uuid import uuid4

from pydantic import Field, BaseModel, EmailStr, UUID4

from backend.main.db.mixins import SessionLevel, PydanticObjectId
from backend.main.db.models.student_profile_model import Guardian


class StudentMeetingRegistration(BaseModel):
    meeting_id: UUID4 = Field()
    student_id: PydanticObjectId = Field()
    registered: bool


class StudentMeetingAttendance(BaseModel):
    meeting_id: UUID4 = Field()
    student_id: PydanticObjectId = Field()
    attended: bool


class StudentMeetingInfo(BaseModel):
    student_id: PydanticObjectId = Field()
    email: EmailStr = Field()
    guardians: List[Guardian] = Field()
    account_uuid: UUID4 = Field()
    attended: bool = Field(default=False)


class CreateMeetingModel(BaseModel):
    date_and_time: datetime = Field()
    duration: int = Field()
    zoom_link: str = Field()
    session_level: SessionLevel = Field()
    topic: Optional[str] = Field()
    miro_link: Optional[str] = Field()
    coordinator_notes: Optional[str] = Field(default=None)
    student_notes: Optional[str] = Field(default=None)
    materials_uploaded: Optional[bool] = Field(default=False)
    materials_object_name: Optional[str] = Field(default=None)


class MeetingModel(CreateMeetingModel):
    uuid: UUID4 = Field(default_factory=uuid4)
    students: List[StudentMeetingInfo] = Field()
    password: str = Field()


class UpdateMeeting(CreateMeetingModel):
    meeting_id: UUID4 = Field()


class MeetingIdModel(BaseModel):
    meeting_id: UUID4 = Field()


class MeetingSearchModel(BaseModel):
    session_levels: Optional[List[SessionLevel]]
    dates: Optional[List[date]]
