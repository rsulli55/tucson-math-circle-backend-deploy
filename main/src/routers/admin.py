from fastapi import Depends, APIRouter, HTTPException, status, BackgroundTasks
from pydantic import UUID4
from starlette.responses import JSONResponse

from backend.main.email_handler.email_handler import EmailSchema, email_handler

from backend.main.src.routers.student import (
    student_meeting_index,
    update_meeting_count,
)

# main db imports
from backend.main.db.models.student_models import StudentVerification
from backend.main.db.docs.student_doc import StudentDocument
from backend.main.db.docs.student_profile_doc import (
    StudentProfileDocument,
)
from backend.main.db.models.meeting_model import (
    CreateMeetingModel,
    MeetingSearchModel,
    MeetingModel,
    UpdateMeeting,
    StudentMeetingAttendance,
    MeetingIdModel,
)
from backend.main.db.docs.meeting_doc import (
    document as MeetingDoc,
    MeetingDocument,
)
from backend.main.db.password_generator import generate_random_password
from backend.main.db.mixins import PydanticObjectId

# auth db imports
from backend.auth.dependencies import (
    TokenData,
    get_admin_token_data,
    create_presigned_url,
)

router = APIRouter()


def update_attendance(
    meeting_doc: MeetingDocument, attendance: StudentMeetingAttendance
):
    st_query = StudentDocument.objects(id=attendance.student_id)
    if len(st_query) < 1:
        print("ERROR: update_student_attendance, could not find Student Document")
    else:
        student = st_query[0]
        student.meetings_registered[str(attendance.meeting_id)] = attendance.attended
        update_count = 1 if attendance.attended else -1
        update_meeting_count(student, meeting_doc.session_level, attended=update_count)
        student.save()

    index = student_meeting_index(meeting_doc, attendance.student_id)
    if index is not None:
        meeting_doc.students[index]["attended"] = attendance.attended
        meeting_doc.save()
    else:
        print("ERROR: update_student_attendance, student not registered for meeting")


# GET routes
@router.get("/get_student_profiles")
def get_student_profiles(token_data: TokenData = Depends(get_admin_token_data)):
    all_profiles = []
    for profile in StudentProfileDocument.objects():
        all_profiles.append(profile.dict())
    return all_profiles


@router.post("/send_reminder_email")
def send_reminder_email(token_data: TokenData = Depends(get_admin_token_data)):
    # TODO:setup student doc for verified email
    pass


@router.post("/send_new_meeting_email")
def send_new_meeting_email(
    background_task: BackgroundTasks,
    meeting_id: str,
    token_data: TokenData = Depends(get_admin_token_data),
):
    meeting = MeetingDocument.objects(id=meeting_id).first()
    students = StudentProfileDocument.objects(mailing_lists__in=meeting.session_level)
    emails = []
    for student in students:
        emails.append(student.email)
    body = (
        """
        <html>
            <body>
                <p>A new meeting has been posted to the Tucson Math Circle website</p>
        """
        + f"<p>Date: {meeting.date_and_time.date}"
        + f"<br>Time: {meeting.date_and_time.time}-{create_meeting.duration.time}"
        + f"<br>Topic: {meeting.topic}"
        + f"<br>Zoom Link: {meeting.zoom_link}"
        + f"<br>Zoom Password: {meeting.password}"
        + f"<br>Miro Link: {meeting.miro_link}"
        + f"<br>Session Level: {meeting.session_level}</p>"
        + """
            </body>
        </html>
        """
    )
    new_email = EmailSchema(
        receivers=emails, subject="New meeting Published", body=body
    )
    background_task.add_task(email_handler, new_email)
    return JSONResponse(status_code=200, content={"message": "email has been sent"})


@router.get("/get_student_profile")
def get_student_profile(
    account_uuid: UUID4, token_data: TokenData = Depends(get_admin_token_data)
):
    pr_query = StudentProfileDocument.objects(uuid=account_uuid)
    if len(pr_query) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not find account with that account_uuid",
        )

    profile = pr_query[0]
    return profile.dict()


@router.get("/get_student_consent_form_url")
async def get_student_consent_form_url(
    student_id: PydanticObjectId, token_data: TokenData = Depends(get_admin_token_data)
):
    st_query = StudentDocument.objects(id=student_id)
    if len(st_query) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not find student with id {student_id}",
        )

    student = st_query[0]
    object_name = student.consent_form_object_name
    if object_name is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student has not uploaded consent form yet",
        )

    response = create_presigned_url(object_name)
    if response is not None:
        return response

    return {"details": "Could not generate presigned url"}


@router.get("/get_meeting_material_url")
async def get_meeting_material_url(
    meeting_uuid: UUID4, token_data: TokenData = Depends(get_admin_token_data)
):
    meeting_query = MeetingDocument.objects(uuid=meeting_uuid)
    if len(meeting_query) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not find meeting with uuid {meeting_uuid}",
        )

    meeting = meeting_query[0]
    object_name = meeting.materials_object_name
    if object_name is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meeting does not have a materials_object_name",
        )

    response = create_presigned_url(object_name)
    if response is not None:
        return response

    return {"details": "Could not generate presigned url"}


# POST routes
@router.post("/get_meetings")
async def get_meetings_by_filter(
    search: MeetingSearchModel, token_data: TokenData = Depends(get_admin_token_data)
):
    # TODO: Use the dates field from MeetingSearchModel
    meetings = []
    try:
        for level in search.session_levels:
            for meeting in MeetingDocument.objects(session_level=level):
                meetings.append(meeting.admin_dict())
    except Exception as e:
        print(e)
        return {"details": "Error finding meeting"}
    return meetings


@router.post("/create_meeting")
async def create_meeting(
    create_meeting: CreateMeetingModel,
    token_data: TokenData = Depends(get_admin_token_data),
):
    password = generate_random_password()
    meeting = MeetingModel(**create_meeting.dict(), password=password, students=[])
    doc = MeetingDoc(meeting)
    doc.save()
    return doc.admin_dict()


# DELETE routes
@router.delete("/delete_meeting")
async def delete_meeting(meeting: MeetingIdModel):
    try:
        meeting_doc = MeetingDocument.objects(uuid=meeting.meeting_id)[0]
    except Exception:
        return "Could not find the meeting"
    meeting_doc.delete()


# PUT routes
@router.put("/update_student_attendance")
async def update_student_attendance(
    attendance: StudentMeetingAttendance,
    token_data: TokenData = Depends(get_admin_token_data),
):
    try:
        meeting_doc = MeetingDocument.objects(uuid=attendance.meeting_id)[0]
    except Exception:
        return "Could not find the meeting"

    update_attendance(meeting_doc, attendance)
    return {"details": f"Updated attendance for student id {attendance.student_id}"}


@router.put("/update_student_verification")
async def update_student_verification(
    verification: StudentVerification,
    token_data: TokenData = Depends(get_admin_token_data),
):
    st_query = StudentDocument.objects(id=verification.student_id)
    if len(st_query) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not find student with that student_id",
        )
    student = st_query[0]
    student.verification_status = verification.status
    student.save()
    return {
        "details": f"Updated verification status for student id {verification.student_id}"
    }


@router.put("/update_meeting")
async def update_meeting(
    update_meeting_model: UpdateMeeting,
    token_data: TokenData = Depends(get_admin_token_data),
):
    meeting_doc = None
    try:
        meeting_doc = MeetingDocument.objects(uuid=update_meeting_model.meeting_id)[0]
    except Exception:
        print("Could not find the meeting")
    meeting_doc.date_and_time = update_meeting_model.date_and_time
    meeting_doc.duration = update_meeting_model.duration
    meeting_doc.zoom_link = update_meeting_model.zoom_link
    meeting_doc.session_level = update_meeting_model.session_level
    meeting_doc.topic = update_meeting_model.topic
    meeting_doc.miro_link = update_meeting_model.miro_link
    meeting_doc.coordinator_notes = update_meeting_model.coordinator_notes
    meeting_doc.student_notes = update_meeting_model.student_notes
    meeting_doc.materials_uploaded = update_meeting_model.materials_uploaded
    meeting_doc.materials_object_name = update_meeting_model.materials_object_name
    meeting_doc.save()
    return meeting_doc.admin_dict()
