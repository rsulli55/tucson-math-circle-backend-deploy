from pydantic import UUID4

from backend.main.db.models.meeting_model import MeetingModel
from backend.main.db.docs.meeting_doc import MeetingDocument, document
from backend.main.db.password_generator import generate_random_password
from backend.main.db.models.meeting_model import StudentMeetingInfo
from fastapi import Depends, APIRouter
from backend.main.src.routers.user_router import get_current_user_doc

# auth db imports
from backend.auth.dependencies import (
    TokenData,
    get_current_token_data,
)

router = APIRouter()


# Some of these are probably broken now.
# Sorry, I will try and fix them if you think we should still use them


@router.post("/add_meeting")
async def add_meeting(meeting: MeetingModel):
    password = generate_random_password()
    meeting.password = password
    meeting.students = []
    doc = document(meeting)
    doc.save()
    return doc.dict()


@router.get("get_meeting_by_id")
async def get_meeting_by_id(
    meeting_id: UUID4, token_data: TokenData = Depends(get_current_token_data)
):
    try:
        meeting = MeetingDocument.objects(uuid=meeting_id)[0]
    except Exception:
        return {"details": "Error getting meeting"}
    if meeting is None:
        return {"details": "could not find meeting form id"}
    return meeting.dict()


@router.post("/get_meetings_by_filter")
async def get_meetings_by_filter(
    filters: list, token_data: TokenData = Depends(get_current_token_data)
):
    meeting_list = []
    try:
        for filter in filters:
            meetings = MeetingDocument.objects(session_level=filter)
            for meeting in meetings:
                meeting_list.append(meeting.dict())
    except Exception:
        return {"details": "Error finding meeting"}
    return meeting_list


@router.post("/get_all_meetings")
async def get_all_meetings(token_data: TokenData = Depends(get_current_token_data)):
    try:
        meetings = MeetingDocument.objects()
    except Exception:
        return {"details": "Error finding meeting"}
    ret_meetings = []
    for meeting in meetings:
        ret_meetings.append(meeting.dict())
    return ret_meetings


@router.put("/update_student")
async def update_student_meeting(
    meeting_id: UUID4,
    student_first: str,
    student_last: str,
    token_data: TokenData = Depends(get_current_token_data),
):
    current_user = get_current_user_doc(token_data)
    try:
        meeting = MeetingDocument.objects(uuid=meeting_id)[0]
    except Exception:
        return {"details": "could not find meeting form id"}

    add_student = {}
    for student in current_user.students:
        if student_first == student.first_name and student_last == student.last_name:
            add_student = student

    add = StudentMeetingInfo(
        first_name=add_student["first_name"],
        last_name=add_student["last_name"],
        email=current_user.email,
        guardians=current_user.guardians,
    )
    meeting.students.append(add.dict())
    meeting.save()
    return {"details": "Student added to meeting list"}
