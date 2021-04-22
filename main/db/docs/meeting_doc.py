from backend.main.db.models.meeting_model import MeetingModel
from backend.main.db.docs.student_doc import StudentDocument
from mongoengine import (
    Document,
    StringField,
    ListField,
    DateTimeField,
    QuerySet,
    UUIDField,
    BooleanField,
    IntField,
)


class MeetingQuerySet(QuerySet):
    pass


def document(model: MeetingModel):
    doc = MeetingDocument(**model.dict())
    return doc


class MeetingDocument(Document):
    _model = MeetingModel

    uuid = UUIDField(required=True)
    date_and_time = DateTimeField(required=True)
    duration = IntField(required=True)
    zoom_link = StringField(required=True)
    topic = StringField(required=True)
    session_level = StringField(required=True)
    miro_link = StringField(required=True)
    password = StringField(required=True)
    students = ListField(required=False)
    coordinator_notes = StringField(reguired=False)
    student_notes = StringField(reguired=False)
    materials_uploaded = BooleanField(required=False)
    materials_object_name = StringField(required=False)

    meta = {
        "query_class": MeetingQuerySet,
        "db_alias": "meeting-db",
        "indexes": ["session_level"],
    }

    def student_dict(self):
        return {
            "uuid": self.uuid,
            "date_and_time": self.date_and_time,
            "duration": self.duration,
            "zoom_link": self.zoom_link,
            "miro_link": self.miro_link,
            "topic": self.topic,
            "session_level": self.session_level,
            "student_notes": self.student_notes,
            "materials_uploaded": self.materials_uploaded,
        }

    def admin_dict(self):
        students_to_return = []
        for st in self.students:
            query = StudentDocument.objects(id=st["student_id"])
            if len(query) < 1:
                print(
                    f"ERROR: student_id {st.student_id} in MeetingDocument but StudentDocument does not exist"
                )
            else:
                student = query[0]
                st["first_name"] = student.first_name
                st["last_name"] = student.last_name

            students_to_return.append(st)

        return {
            "uuid": self.uuid,
            "date_and_time": self.date_and_time,
            "duration": self.duration,
            "zoom_link": self.zoom_link,
            "miro_link": self.miro_link,
            "topic": self.topic,
            "session_level": self.session_level,
            "password": self.password,
            "students": students_to_return,
            "coordinator_notes": self.coordinator_notes,
            "student_notes": self.student_notes,
            "materials_uploaded": self.materials_uploaded,
        }

    def dict(self):
        students_to_return = []
        for st in self.students:
            query = StudentDocument.objects(id=st["student_id"])
            if len(query) < 1:
                print(
                    f"ERROR: student_id {st.student_id} in MeetingDocument but StudentDocument does not exist"
                )
            else:
                student = query[0]
                st["first_name"] = student.first_name
                st["last_name"] = student.last_name

            students_to_return.append(st)

        return {
            "uuid": self.uuid,
            "date_and_time": self.date_and_time,
            "duration": self.duration,
            "zoom_link": self.zoom_link,
            "miro_link": self.miro_link,
            "topic": self.topic,
            "session_level": self.session_level,
            "password": self.password,
            "students": students_to_return,
            "coordinator_notes": self.coordinator_notes,
            "student_notes": self.student_notes,
            "materials_uploaded": self.materials_uploaded,
        }
