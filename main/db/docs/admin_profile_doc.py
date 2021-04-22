from backend.main.db.models.admin_profile_model import AdminProfileModel
from mongoengine import Document, StringField, ListField, EmailField


def document(model: AdminProfileModel):
    doc = AdminProfileDocument(**model.dict())
    return doc


class AdminProfileDocument(Document):
    _model = AdminProfileModel

    first_name = StringField(required=True)
    last_name = StringField(required=True)
    username = StringField(required=True)
    phone_number = StringField(required=False)
    section_access = ListField(required=True)
    email = EmailField(required=True)

    meta = {"db_alias": "admin-db"}

    def dict(self):
        return {
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone_number": self.phone_number,
            "section_access": self.section_access,
        }
