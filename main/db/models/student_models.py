from typing import Dict, Optional
from enum import Enum

from pydantic import BaseModel, Field, UUID4

from backend.main.db.mixins import PydanticObjectId, SessionLevel


class StudentMeetingCounter(BaseModel):
    attended: int = 0
    registered: int = 0
    # TODO: Add a validation that attended <= registered


class StudentMeetingRegistration(BaseModel):
    meeting_uuid: UUID4 = Field()
    attended: bool = False


# used for `admin/update_student_verification` route
class StudentVerification(BaseModel):
    student_id: PydanticObjectId
    status: bool


class StudentGrade(str, Enum):
    pre_k = "PreK"
    k = "K"
    one = "1"
    two = "2"
    three = "3"
    four = "4"
    five = "5"
    six = "6"
    seven = "7"
    eight = "8"
    nine = "9"
    ten = "10"
    eleven = "11"
    twelve = "12"


class StudentCreateModel(BaseModel):
    first_name: str = Field()
    last_name: str = Field()
    grade: StudentGrade = Field()
    birth_month: Optional[int] = None
    birth_year: Optional[int] = None
    verification_status: bool = False
    consent_form_object_name: Optional[str] = None


class StudentUpdateModel(StudentCreateModel):
    # if `id` is None, that means this is a new student
    id: Optional[PydanticObjectId] = None


class StudentModel(StudentCreateModel):
    profile_uuid: UUID4 = Field()
    # dictionary of the form (meeting uuid, attended (True/False))
    meetings_registered: Dict[UUID4, bool] = {}
    # meeting_counts is a convenience to track the number
    # of meetings registered and attended for each `SessionLevel`
    meeting_counts: Dict[SessionLevel, StudentMeetingCounter] = {
        SessionLevel.junior_a: StudentMeetingCounter(),
        SessionLevel.junior_b: StudentMeetingCounter(),
        SessionLevel.senior: StudentMeetingCounter(),
    }
