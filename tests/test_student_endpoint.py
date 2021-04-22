from fastapi.testclient import TestClient
import toml
import pytest
from json import JSONEncoder
from pathlib import Path
from uuid import UUID
from backend.main.src.app import app
from backend.auth.main import app as auth_app
from mongoengine import disconnect_all, connect
from backend.auth.db.main import connect_to_db
from backend.tests.pre_save_meetings import pre_save_meetings
from backend.main.db.models.meeting_model import (
    MeetingSearchModel,
    StudentMeetingRegistration,
)
from backend.main.db.docs.meeting_doc import MeetingDocument
from backend.main.db.models.student_models import StudentCreateModel, StudentGrade
from backend.main.db.models.student_profile_model import (
    StudentProfileCreateModel,
    Guardian,
    SessionLevel,
    StudentUpdateModel,
)
from backend.main.db.docs.student_profile_doc import StudentProfileDocument

CONFIG_PATH = Path(__file__).resolve().parents[1].joinpath("auth/db-config.toml")
print("Using CONFIG_PATH:", CONFIG_PATH)

config = toml.load(str(CONFIG_PATH))

db_username = config["atlas-username"]
db_password = config["atlas-password"]
db_uri = config["connection-uri"]
auth_db = config["auth-db"]
connect_to_db(
    db_uri.format(username=db_username, password=db_password, database=auth_db)
)

student = StudentProfileCreateModel(
    email="jaketeststudent@email.com",
    students=[
        StudentCreateModel(
            first_name="jake",
            last_name="lasalle",
            grade=StudentGrade("5"),
            age=11,
            verification_status=False,
        )
    ],
    guardians=[
        Guardian(
            first_name="jimmy",
            last_name="smith",
            phone_number="123456789",
            email="jaketeststudent@email.com",
        )
    ],
    mailing_lists=[SessionLevel("junior_a")],
)

student_extra_student = StudentProfileCreateModel(
    email="jimmyteststudent@email.com",
    students=[
        StudentUpdateModel(
            id=None,
            first_name="jake",
            last_name="lasalle",
            grade=StudentGrade("6"),
            age=11,
            verification_status=False,
        ),
        StudentUpdateModel(
            first_name="jimmy",
            last_name="lasalle",
            grade=StudentGrade("2"),
            age=6,
            verification_status=False,
        ),
    ],
    guardians=[
        Guardian(
            first_name="jimmy",
            last_name="smith",
            phone_number="123456789",
            email="jaketeststudent@email.com",
        )
    ],
    mailing_lists=[SessionLevel("junior_a")],
)

student2 = StudentProfileCreateModel(
    email="jimmyteststudent@email.com",
    students=[
        StudentCreateModel(
            first_name="jimmy",
            last_name="Smithers",
            grade=StudentGrade("7"),
            age=11,
            verification_status=False,
        )
    ],
    guardians=[
        Guardian(
            first_name="jimmy",
            last_name="smithers",
            phone_number="123456789",
            email="jimmyteststudent@email.com",
        )
    ],
    mailing_lists=[SessionLevel("junior_a")],
)

student3 = StudentProfileCreateModel(
    email="johnnyteststudent@email.com",
    students=[
        StudentCreateModel(
            first_name="johhny",
            last_name="Smith",
            grade=StudentGrade("6"),
            age=11,
            verification_status=False,
        )
    ],
    guardians=[
        Guardian(
            first_name="jimmy",
            last_name="paul",
            phone_number="123456789",
            email="johnnyteststudent@email.com",
        )
    ],
    mailing_lists=[SessionLevel("junior_a")],
)


JSONEncoder_olddefault = JSONEncoder.default


def JSONEncoder_newdefault(self, o):
    if isinstance(o, UUID):
        return str(o)
    return JSONEncoder_olddefault(self, o)


JSONEncoder.default = JSONEncoder_newdefault


def pre_save_user_auths():
    client2.post(
        "/student/register",
        json={
            "email": "jaketeststudent@email.com",
            "role": "student",
            "password": "password",
        },
    )
    client2.post(
        "/student/register",
        json={
            "email": "jimmyteststudent@email.com",
            "role": "student",
            "password": "password",
        },
    )
    client2.post(
        "/student/register",
        json={
            "email": "johnnyteststudent@email.com",
            "role": "student",
            "password": "password",
        },
    )


def pre_save_profile_docs():
    response = client2.post(
        "/token", data={"username": "jaketeststudent@email.com", "password": "password"}
    )
    access_token = response.json()["access_token"]
    client.post(
        "/student/add_profile",
        json=student.dict(),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response = client2.post(
        "/token",
        data={"username": "jimmyteststudent@email.com", "password": "password"},
    )
    access_token = response.json()["access_token"]
    client.post(
        "/student/add_profile",
        json=student2.dict(),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response = client2.post(
        "/token",
        data={"username": "johnnyteststudent@email.com", "password": "password"},
    )
    access_token = response.json()["access_token"]
    client.post(
        "/student/add_profile",
        json=student3.dict(),
        headers={"Authorization": f"Bearer {access_token}"},
    )


@pytest.fixture()
def mock_database():
    disconnect_all()
    connect(host="mongomock://localhost", db="mongoenginetest", alias="student-db")
    connect(host="mongomock://localhost", db="mongoenginetest", alias="meeting-db")
    connect(host="mongomock://localhost", db="mongoenginetest", alias="admin-db")


client = TestClient(app)
client2 = TestClient(auth_app)


def test_add_profile(mock_database):
    pre_save_user_auths()
    response = client2.post(
        "/token", data={"username": "jaketeststudent@email.com", "password": "password"}
    )
    json = response.json()
    access_token = json["access_token"]
    response = client.post(
        "/student/add_profile",
        json=student.dict(),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    docs = StudentProfileDocument.objects(email="jaketeststudent@email.com")
    assert len(docs) == 1
    assert docs[0].email == "jaketeststudent@email.com"
    assert docs[0].students[0]["first_name"] == "jake"


def test_get_my_profile(mock_database):
    pre_save_user_auths()
    pre_save_profile_docs()
    response = client2.post(
        "/token", data={"username": "jaketeststudent@email.com", "password": "password"}
    )
    json = response.json()
    access_token = json["access_token"]
    response = client.get(
        "/student/get_my_profile", headers={"Authorization": f"Bearer {access_token}"}
    )
    json = response.json()
    assert json["email"] == "jaketeststudent@email.com"
    assert len(json["student_list"]) == 1


def test_get_students(mock_database):
    pre_save_user_auths()
    pre_save_profile_docs()
    response = client2.post(
        "/token", data={"username": "jaketeststudent@email.com", "password": "password"}
    )
    json = response.json()
    access_token = json["access_token"]
    response = client.get(
        "/student/get_students", headers={"Authorization": f"Bearer {access_token}"}
    )
    json = response.json()
    assert len(json) == 1


def test_update_student_profile(mock_database):
    pre_save_user_auths()
    pre_save_profile_docs()
    response = client2.post(
        "/token",
        data={"username": "jimmyteststudent@email.com", "password": "password"},
    )
    json = response.json()
    access_token = json["access_token"]
    response = client.get(
        "/student/get_my_profile", headers={"Authorization": f"Bearer {access_token}"}
    )
    json = response.json()
    student_id = json["student_list"][0]["id"]
    student_extra_student.students[0].id = student_id
    response = client.put(
        "/student/update_profile",
        json=student_extra_student.dict(),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    json = response.json()
    assert len(json["student_list"]) == 2


def test_get_meetings(mock_database):
    pre_save_user_auths()
    pre_save_profile_docs()
    pre_save_meetings()
    response = client2.post(
        "/token",
        data={"username": "jimmyteststudent@email.com", "password": "password"},
    )
    json = response.json()
    access_token = json["access_token"]
    client.post(
        "/student/get_meetings",
        json=MeetingSearchModel(session_levels=[SessionLevel("junior_a")]).dict(),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    meetings = MeetingDocument.objects()
    assert len(meetings) == 3


def test_update_student_for_meeting(mock_database):
    pre_save_user_auths()
    pre_save_profile_docs()
    pre_save_meetings()
    response = client2.post(
        "/token",
        data={"username": "jimmyteststudent@email.com", "password": "password"},
    )
    student_doc = StudentProfileDocument.objects(email="jimmyteststudent@email.com")[0]
    student_id = student_doc.students[0].id
    meeting = MeetingDocument.objects()[0]
    json = response.json()
    access_token = json["access_token"]
    client.post(
        "/student/update_student_for_meeting",
        json=StudentMeetingRegistration(
            meeting_id=meeting.uuid,
            student_id=student_id,
            registered=True,
        ).dict(),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    meetings = MeetingDocument.objects(uuid=meeting.uuid)[0]
    assert len(meetings.students) == 1
    assert meetings.students[0]["student_id"] == str(student_id)
    client.post(
        "/student/update_student_for_meeting",
        json=StudentMeetingRegistration(
            meeting_id=meeting.uuid,
            student_id=student_id,
            registered=False,
        ).dict(),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    meetings = MeetingDocument.objects(uuid=meeting.uuid)[0]
    assert len(meetings.students) == 0
