from pydantic import BaseModel, EmailStr, Field
from fastapi import Depends, APIRouter

# main db imports
from backend.main.db.models.student_profile_model import (
    StudentProfileModel,
    StudentProfileCreateModel,
)
from backend.main.db.docs.student_profile_doc import (
    document as StudentDoc,
    StudentProfileDocument,
)
from backend.main.db.models.student_profile_model import Guardian, Student

# auth db imports
from backend.auth.dependencies import (
    TokenData,
    get_student_token_data,
)

router = APIRouter()


class Email(BaseModel):
    new_email: EmailStr = Field()


def get_current_user_doc(token_data: TokenData):
    current_user = None
    try:
        current_user = StudentProfileDocument.objects(uuid=token_data.id)[0]
    except Exception as e:
        print("Exception type:", type(e))
        print("Could not find the user profile.")
    return current_user


# GET routes
@router.get("/get_my_profile")
def get_current_user_profile(token_data: TokenData = Depends(get_student_token_data)):
    user_doc = None
    try:
        user_doc = StudentProfileDocument.objects(uuid=token_data.id)[0]
    except Exception as e:
        print("Exception type:", type(e))
        print("Could not find the user profile.")
    return user_doc.dict()


# POST routes
@router.post("/add_student_profile")
async def add_student_profile(
    profile: StudentProfileCreateModel,
    token_data: TokenData = Depends(get_student_token_data),
):
    model = StudentProfileModel(**profile.dict(), uuid=token_data.id)
    doc = StudentDoc(model)
    doc.save()
    return doc.dict()


# PUT routes
@router.put("/update_student_profile")
async def update_main_email(
    email: Email,
    token_data: TokenData = Depends(get_student_token_data),
):
    current_user = get_current_user_doc(token_data)
    if current_user.email != email.new_email:
        current_user.email = email.new_email
    current_user.save()
    return current_user.dict()


@router.put("/update_student_guardian")
async def update_student_guardian(
    guardian: Guardian,
    token_data: TokenData = Depends(get_student_token_data),
):
    current_user = get_current_user_doc(token_data)
    updated_contact = None
    i = 0
    for contact in current_user.guardians:
        if (
            contact["first_name"] == guardian.first_name
            and contact["last_name"] == guardian.last_name
        ):
            updated_contact = contact
            break
        i += 1

    if updated_contact is None:
        return {"details": "The contact could not be found."}

    current_user.guardians[i] = guardian.dict()

    current_user.save()
    return current_user.dict()


@router.put("/add_student_guardian")
async def add_student_guardian(
    guardian: Guardian,
    token_data: TokenData = Depends(get_student_token_data),
):
    current_user = get_current_user_doc(token_data)
    updated_contact = None
    for contact in current_user.guardians:
        if (
            contact["first_name"] == guardian.first_name
            and contact["last_name"] == guardian.last_name
        ):
            updated_contact = contact

    if updated_contact is not None:
        return {"details": "The contact is already in the list"}

    current_user.guardians.append(guardian.dict())
    current_user.save()
    return current_user.dict()


@router.put("/add_student")
async def add_student(
    student: Student,
    token_data: TokenData = Depends(get_student_token_data),
):
    current_user = get_current_user_doc(token_data)
    add_student = None
    for add in current_user.students:
        if (
            add["first_name"] == student.first_name
            and add["last_name"] == student.last_name
        ):
            add_student = add

    if add_student is not None:
        return {"details": "The student is already in the list"}

    current_user.students.append(student.dict())
    current_user.save()
    return current_user.dict()


@router.put("/update_student")
async def update_student(
    student: Student,
    token_data: TokenData = Depends(get_student_token_data),
):
    current_user = get_current_user_doc(token_data)
    add_student = None
    i = 0
    for add in current_user.students:
        if (
            add["first_name"] == student.first_name
            and add["last_name"] == student.last_name
        ):
            add_student = add
            break
        i += 1

    if add_student is None:
        return {"details": "The student could not be found"}

    current_user.students[i] = student.dict()

    current_user.save()
    return current_user.dict()
