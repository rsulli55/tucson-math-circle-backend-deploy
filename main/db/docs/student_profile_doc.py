from mongoengine import (
    Document,
    ListField,
    EmailField,
    QuerySet,
    UUIDField,
    ReferenceField,
)

from backend.main.db.models.student_profile_model import (
    StudentProfileModel,
)

from backend.main.db.docs.student_doc import StudentDocument, document as StudentDoc


class StudentProfileQuerySet(QuerySet):
    pass


def document(model: StudentProfileModel):
    # create StudentDocument for each student in the student profile
    student_documents = []
    for student in model.students:
        student_document = StudentDoc(student)
        student_document.save()
        student_documents.append(student_document)

    guardians = [g.dict() for g in model.guardians]
    doc = StudentProfileDocument(
        uuid=model.uuid,
        email=model.email,
        students=student_documents,
        guardians=guardians,
        mailing_lists=model.mailing_lists,
    )
    return doc


class StudentProfileDocument(Document):
    _model = StudentProfileModel

    # TODO: change `student_list` to `students`?
    uuid = UUIDField(required=True)
    email = EmailField(required=True)
    students = ListField(ReferenceField(StudentDocument))
    guardians = ListField(required=True)
    mailing_lists = ListField(required=False)

    meta = {
        "query_class": StudentProfileQuerySet,
        "db_alias": "student-db",
        "indexes": ["email", "uuid"],
    }

    def dict(self):
        students = [s.dict() for s in self.students]
        return {
            "uuid": self.uuid,
            "email": self.email,
            "student_list": students,
            "guardians": self.guardians,
            "mailing_lists": self.mailing_lists,
        }
