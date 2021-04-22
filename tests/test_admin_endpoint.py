from fastapi.testclient import TestClient
import toml
import pytest
from pathlib import Path
from json import JSONEncoder
from uuid import UUID
from datetime import datetime

# hack to add project directory to path and make modules work nicely
import sys
from pathlib import Path

PROJECTS_DIR = Path(__file__).resolve().parents[2]
print("Appending PROJECTS_DIR to PATH:", PROJECTS_DIR)
sys.path.append(str(PROJECTS_DIR))

from backend.main.src.app import app
from backend.auth.main import app as auth_app
from mongoengine import disconnect_all, connect
from backend.auth.db.main import connect_to_db
from backend.main.db.password_generator import generate_random_password
from backend.main.db.docs.meeting_doc import MeetingDocument
from backend.main.db.models.meeting_model import (
    MeetingModel,
    CreateMeetingModel,
    UpdateMeeting,
    StudentMeetingAttendance,
    MeetingSearchModel,
    StudentMeetingRegistration,
)
from backend.tests.test_student_endpoint import (
    pre_save_user_auths,
    pre_save_profile_docs,
)
from backend.main.db.models.student_profile_model import SessionLevel
from backend.main.db.models.student_models import StudentVerification
from backend.main.db.docs.student_doc import StudentDocument
from backend.main.db.docs.student_profile_doc import StudentProfileDocument
from backend.tests.pre_save_meetings import pre_save_meetings

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


JSONEncoder_olddefault = JSONEncoder.default


def JSONEncoder_newdefault(self, o):
    if isinstance(o, UUID):
        return str(o)
    elif isinstance(o, datetime):
        return str(o)
    return JSONEncoder_olddefault(self, o)


JSONEncoder.default = JSONEncoder_newdefault


test_meeting_model = CreateMeetingModel(
    date_and_time=datetime.utcnow(),
    duration=60,
    zoom_link="zoomlink",
    session_level=SessionLevel("junior_a"),
    topic="test_topic",
    miro_link="miro_link",
)

meeting1 = MeetingModel(
    **CreateMeetingModel(
        date_and_time="2021-03-20T18:00:00.860+00:00",
        duration=60,
        zoom_link="test_zoom_link",
        session_level=SessionLevel("junior_a"),
        topic="test_topic",
        miro_link="test_miro_link",
    ).dict(),
    password=generate_random_password(),
    students=[],
)

meeting_search = MeetingSearchModel(session_levels=[SessionLevel("junior_a")])


@pytest.fixture()
def mock_database():
    disconnect_all()
    connect(host="mongomock://localhost", db="mongoenginetest", alias="student-db")
    connect(host="mongomock://localhost", db="mongoenginetest", alias="meeting-db")
    connect(host="mongomock://localhost", db="mongoenginetest", alias="admin-db")


client = TestClient(app)
client2 = TestClient(auth_app)


def test_get_all_students(mock_database):
    pre_save_user_auths()
    pre_save_profile_docs()
    response = client2.post(
        "/token", data={"username": "admin@email.com", "password": "password"}
    )
    json = response.json()
    access_token = json["access_token"]
    response = client.get(
        "/admin/get_student_profiles",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    students = response.json()
    assert len(students) == 3


def test_get_student(mock_database):
    pre_save_user_auths()
    pre_save_profile_docs()
    response = client2.post(
        "/token", data={"username": "admin@email.com", "password": "password"}
    )
    account_id = StudentProfileDocument.objects().first().uuid
    json = response.json()
    access_token = json["access_token"]
    response = client.get(
        "/admin/get_student_profile",
        json=account_id,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    student = response.json()
    assert len(student) == 1


def test_create_meeting(mock_database):
    response = client2.post(
        "/token", data={"username": "admin@email.com", "password": "password"}
    )
    json = response.json()
    access_token = json["access_token"]
    response = client.post(
        "/admin/create_meeting",
        json=test_meeting_model.dict(),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    meeting = MeetingDocument.objects()
    json = response.json()
    assert len(meeting) == 1
    assert json["topic"] == "test_topic"


def test_get_meeting_by_filter(mock_database):
    pre_save_meetings()
    response = client2.post(
        "/token", data={"username": "admin@email.com", "password": "password"}
    )
    json = response.json()
    access_token = json["access_token"]
    response = client.post(
        "/admin/get_meetings",
        json=meeting_search.dict(),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    json = response.json()
    assert len(json) == 2


def test_delete_meeting(mock_database):
    pre_save_meetings()
    meeting = MeetingDocument.objects()[0]
    id = meeting.uuid
    response = client.delete("/admin/delete_meeting", json={"meeting_id": f"{id}"})
    assert response.status_code == 200
    meeting = MeetingDocument.objects(uuid=id)
    assert len(meeting) == 0


def add_student_to_meeting():
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
    return student_id


def test_update_student_attendance(mock_database):
    pre_save_user_auths()
    pre_save_profile_docs()
    pre_save_meetings()
    response = client2.post(
        "/token", data={"username": "admin@email.com", "password": "password"}
    )
    meeting_id = MeetingDocument.objects().first().uuid
    json = response.json()
    access_token = json["access_token"]
    student_id = add_student_to_meeting()
    response = client.put(
        "/admin/update_student_attendance",
        json=StudentMeetingAttendance(
            meeting_id=meeting_id, student_id=student_id, attended=True
        ).dict(),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    student = StudentDocument.objects(id=student_id).first()
    assert student.meeting_counts["junior_a"]["attended"] == 1


def test_update_student_verification(mock_database):
    pre_save_user_auths()
    pre_save_profile_docs()
    response = client2.post(
        "/token", data={"username": "admin@email.com", "password": "password"}
    )
    student_doc = StudentProfileDocument.objects(email="jimmyteststudent@email.com")[0]
    student_id = student_doc.students[0].id
    json = response.json()
    access_token = json["access_token"]
    client.put(
        "/admin/update_student_verification",
        json=StudentVerification(student_id=student_id, status=True).dict(),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    student = StudentDocument.objects(id=student_id).first()
    assert student.verification_status is True


def test_update_meeting(mock_database):
    pre_save_meetings()
    meeting = MeetingDocument.objects()[0]
    id = meeting.uuid
    response = client2.post(
        "/token", data={"username": "admin@email.com", "password": "password"}
    )
    json = response.json()
    access_token = json["access_token"]
    update = UpdateMeeting(**meeting1.dict(), meeting_id=id)
    response = client.put(
        "/admin/update_meeting",
        json=update.dict(),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    meeting = MeetingDocument.objects(uuid=id)[0]
    assert meeting.miro_link == "test_miro_link"
    assert meeting.topic == "test_topic"
    assert meeting.zoom_link == "test_zoom_link"
