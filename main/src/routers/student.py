from fastapi import BackgroundTasks
from starlette.responses import JSONResponse
from fastapi import Depends, APIRouter, HTTPException, status
from backend.main.email_handler.email_handler import EmailSchema, email_handler
from pydantic import UUID4

# main db imports
from backend.main.db.models.student_profile_model import (
    StudentProfileModel,
    StudentProfileCreateModel,
    StudentProfileUpdateModel,
)
from backend.main.db.models.student_models import (
    StudentModel,
    StudentUpdateModel,
)
from backend.main.db.docs.student_doc import (
    document as StudentDoc,
    StudentDocument,
)
from backend.main.db.docs.student_profile_doc import (
    document as ProfileDoc,
    StudentProfileDocument,
)
from backend.main.db.models.meeting_model import (
    MeetingSearchModel,
    StudentMeetingRegistration,
    StudentMeetingInfo,
)
from backend.main.db.docs.meeting_doc import (
    MeetingDocument,
)
from backend.main.db.mixins import PydanticObjectId, SessionLevel


# auth db imports
from backend.auth.dependencies import (
    TokenData,
    get_student_token_data,
    create_presigned_url,
)

router = APIRouter()


def get_current_user_doc(token_data: TokenData):
    current_user = None
    try:
        current_user = StudentProfileDocument.objects(uuid=token_data.id)[0]
    # TODO: raise an HTTP exception instead of just returning details
    except Exception as e:
        print("Exception type:", type(e))
        print("Could not find the user profile.")
    return current_user


def get_student_meeting_index(meeting_doc, first, last):
    i = 0
    while i < len(meeting_doc.students):
        if (
            meeting_doc.students[i].first_name == first
            and meeting_doc.students[i].last_name == last
        ):
            return i
        i += 1
    return i


def student_meeting_index(meeting_doc: MeetingDocument, student_id: PydanticObjectId):
    check_id = lambda reg: reg["student_id"] == student_id
    for i, registration in enumerate(meeting_doc.students):
        if check_id(registration):
            return i
    print("ERROR: get_student_meeting_index could not find student in MeetingDocument")
    return None


def update_meeting_count(
    student: StudentDocument, level: SessionLevel, registered=0, attended=0
):
    """Increment `student`'s `meeting_counts` for SessionLevel `level` according to
    `registered` and `attended`"""
    student.meeting_counts[level]["registered"] += registered
    student.meeting_counts[level]["attended"] += attended


def remove_student_from_meeting(
    meeting_doc: MeetingDocument, student_id: PydanticObjectId
):
    index = student_meeting_index(meeting_doc, student_id)
    if index is not None:
        del meeting_doc.students[index]
        meeting_doc.save()
    else:
        print("ERROR: remove_student_from_meeting student not found in MeetingDocument")


def generate_meeting_registrations(registrations, students):
    # dict of registration status for each student in students
    meeting_registrations = {}
    for i, st in enumerate(students):
        meeting_registrations[str(st.id)] = {
            "id": str(st.id),
            "first_name": st.first_name,
            "last_name": st.last_name,
            "registered": False,
        }

    for registration in registrations:
        reg_id = registration["student_id"]
        if reg_id in meeting_registrations.keys():
            meeting_registrations[reg_id]["registered"] = True

    return meeting_registrations


def update_student_document(student_doc: StudentDocument, updates: StudentUpdateModel):
    student_doc.first_name = updates.first_name
    student_doc.last_name = updates.last_name
    student_doc.grade = updates.grade
    student_doc.birth_month = updates.birth_month
    student_doc.birth_year = updates.birth_year
    student_doc.consent_form_object_name = updates.consent_form_object_name
    student_doc.save()


# GET routes
@router.get("/get_my_profile")
def get_current_user_profile(token_data: TokenData = Depends(get_student_token_data)):
    current_user = get_current_user_doc(token_data)
    return current_user.dict()


@router.get("/get_students")
def get_student_names(token_data: TokenData = Depends(get_student_token_data)):
    current_user = get_current_user_doc(token_data)
    return current_user["students"]


@router.get("/get_consent_form_url")
async def get_student_consent_form_url(
    student_id: PydanticObjectId,
    token_data: TokenData = Depends(get_student_token_data),
):
    st_query = StudentDocument.objects(id=student_id)
    if len(st_query) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not find student with id {student_id}",
        )

    student = st_query[0]
    if student.profile_uuid != token_data.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student id is associated with a different account",
        )

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
    meeting_uuid: UUID4, token_data: TokenData = Depends(get_student_token_data)
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


@router.post("/send_verification_email")
def send_verification_email(
    background_task: BackgroundTasks,
    token_data: TokenData = Depends(get_student_token_data),
):
    current_user = get_current_user_doc(token_data)
    verification_url = "This/Is/The/Verification/Url"
    consent_form_url = "This/Is/The/Consent/Form/Url"
    body = (
        """
        <html>
            <body>
                <p>This email was sent to verify your Tucson Math Circle account</p>
                <p>Please click on the link below to verify your account.</p>
        """
        + f"<p>{verification_url}</p>"
        f"<p>The following link is the link to "
        f"the consent form that you have to fill out and upload to your account</p>"
        f"<p>{consent_form_url}</p>"
        + """
            </body>
        </html>
        """
    )
    new_email = EmailSchema(
        receivers=[current_user.email],
        subject="Verify Email",
        body=body,
        attachment=None,
    )
    background_task.add_task(email_handler, background_task, new_email)
    return JSONResponse(status_code=200, content={"message": "email has been sent"})


@router.put("/verify_email")
def verify_email(token_data: TokenData = Depends(get_student_token_data)):
    # TODO:setup student doc for verified email
    pass


# POST routes
@router.post("/add_profile")
async def add_profile(
    profile: StudentProfileCreateModel,
    token_data: TokenData = Depends(get_student_token_data),
):
    # raise exception if profile already exists
    existing_user = get_current_user_doc(token_data)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A Profile for that account already exists",
        )

    profile_uuid = token_data.id
    # create StudentModels for each student in the student profile
    student_models = []
    for student_create in profile.students:
        student = StudentModel(**student_create.dict(), profile_uuid=profile_uuid)
        student_models.append(student)

    student_profile = StudentProfileModel(
        uuid=token_data.id,
        email=profile.email,
        students=student_models,
        guardians=profile.guardians,
        mailing_lists=profile.mailing_lists,
    )

    # ProfileDoc handles creating StudentDocuments and saving them
    doc = ProfileDoc(student_profile)
    doc.save()
    return doc.dict()


@router.post("/get_meetings")
async def get_meetings_by_filter(
    search: MeetingSearchModel, token_data: TokenData = Depends(get_student_token_data)
):
    current_user = get_current_user_doc(token_data)
    if not current_user:
        print("This account has no profile!")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has no profile",
        )
    current_students = current_user.students

    # TODO: Use the dates field from MeetingSearchModel
    meetings = []
    try:
        for level in search.session_levels:
            for meeting in MeetingDocument.objects(session_level=level):
                registrations = meeting.students
                meeting_registrations = generate_meeting_registrations(
                    registrations, current_students
                )
                meeting_info = meeting.student_dict()
                meeting_info["registrations"] = [
                    meeting_registrations[sid] for sid in meeting_registrations.keys()
                ]
                meetings.append(meeting_info)
    except Exception as e:
        print("Exception type:", type(e))
        return {"details": "Problem in get_meetings_by_filter"}
    return meetings


@router.post("/update_student_for_meeting")
async def update_student(
    registration: StudentMeetingRegistration,
    token_data: TokenData = Depends(get_student_token_data),
):

    current_user = get_current_user_doc(token_data)
    # FIXME: This assumes that the student id given in `registration`
    # is a valid student id for this account
    try:
        student = StudentDocument.objects(id=registration.student_id)[0]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid student id",
        )

    try:
        meeting_doc = MeetingDocument.objects(uuid=registration.meeting_id)[0]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid meeting id",
        )

    meeting_id = str(registration.meeting_id)
    if not registration.registered:
        remove_student_from_meeting(meeting_doc, registration.student_id)
        # Update StudentDocument `meetings_registered` to reflect changes
        if meeting_id in student.meetings_registered:
            # remove registration
            del student.meetings_registered[meeting_id]
            # decrement registered count
            update_meeting_count(student, meeting_doc.session_level, registered=-1)
            student.save()

        return {
            "details": f"Student with id {registration.student_id} removed from meeting list"
        }

    # otherwise add student to meeting
    student_info = StudentMeetingInfo(
        student_id=registration.student_id,
        email=current_user.email,
        guardians=current_user.guardians,
        account_uuid=token_data.id,
    )
    meeting_doc.students.append(student_info.dict())
    meeting_doc.save()

    # Update StudentDocument `meetings_registered`
    if meeting_id not in student.meetings_registered:
        # add the registration
        student.meetings_registered[meeting_id] = False
        # increment registered count
        update_meeting_count(student, meeting_doc.session_level, registered=1)
    student.save()
    return {
        "details": f"Student with id {registration.student_id} added to meeting list"
    }


# PUT routes
@router.put("/update_profile")
async def update_profile(
    new_profile: StudentProfileUpdateModel,
    token_data: TokenData = Depends(get_student_token_data),
):
    current_user = get_current_user_doc(token_data)
    current_user.email = new_profile.email
    current_user.guardians = [g.dict() for g in new_profile.guardians]
    current_user.mailing_lists = new_profile.mailing_lists

    # keep track of id's seen so we know what students to remove from account
    # student id is an Optional
    ids_in_request = [st.id for st in new_profile.students if st.id]
    # remove students not found in request
    for student_doc in current_user.students:
        if str(student_doc.id) not in ids_in_request:
            current_user.update(pull__students=student_doc)

    # update StudentDocuments
    # `new_profile.students` is a `List[StudentUpdateModel]`
    for student_update in new_profile.students:
        # add a new student if id is None
        if not student_update.id:
            new_student = StudentModel(
                **student_update.dict(), profile_uuid=token_data.id
            )
            student_document = StudentDoc(new_student)
            student_document.save()
            current_user.students.append(student_document)

        else:
            query = StudentDocument.objects(id=student_update.id)
            # if the student already existed update it
            if len(query) > 0:
                student_doc = query[0]
                update_student_document(student_doc, student_update)
            else:
                print("ERROR: could not find student id in update_profile")

    current_user.save()
    return current_user.dict()
