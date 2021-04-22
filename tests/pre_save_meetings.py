from backend.main.db.password_generator import generate_random_password
from backend.main.db.docs.meeting_doc import document
from backend.main.db.models.meeting_model import MeetingModel, CreateMeetingModel
from backend.main.db.models.student_profile_model import SessionLevel


meeting1 = MeetingModel(
    **CreateMeetingModel(
        date_and_time="2021-03-20T18:00:00.860+00:00",
        duration=60,
        zoom_link="zoomlink",
        session_level=SessionLevel("junior_a"),
        topic="topic",
        miro_link="miro_link",
    ).dict(),
    password=generate_random_password(),
    students=[]
)

meeting2 = MeetingModel(
    **CreateMeetingModel(
        date_and_time="2021-03-20T18:00:00.860+00:00",
        duration=60,
        zoom_link="zoomlink2",
        session_level=SessionLevel("junior_a"),
        topic="topic2",
        miro_link="miro_link2",
    ).dict(),
    password=generate_random_password(),
    students=[]
)

meeting3 = MeetingModel(
    **CreateMeetingModel(
        date_and_time="2021-03-20T18:00:00.860+00:00",
        duration=120,
        zoom_link="zoomlink3",
        session_level=SessionLevel("junior_b"),
        topic="topic3",
        miro_link="miro_link3",
    ).dict(),
    password=generate_random_password(),
    students=[]
)


def pre_save_meetings():
    doc = document(meeting1)
    doc.save()
    doc2 = document(meeting2)
    doc2.save()
    doc3 = document(meeting3)
    doc3.save()
