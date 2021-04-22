from pathlib import Path

from mongoengine import connect
import toml

from backend.auth.db.main import connect_to_db

# get the config file path
CONFIG_PATH = Path(__file__).resolve().parent.joinpath("auth/db-config.toml")
print("Using CONFIG_PATH:", CONFIG_PATH)

config = toml.load(str(CONFIG_PATH))

db_username = config["atlas-username"]
db_password = config["atlas-password"]
db_uri = config["connection-uri"]
auth_db = config["auth-db"]
meeting_db = config["meeting-db"]
student_db = config["student-db"]


def connect_to_mongodb():
    connect(
        alias="student-db",
        db=student_db,
        host=db_uri.format(
            username=db_username, password=db_password, database=student_db
        ),
        uuidRepresentation="standard",
    )
    connect(
        alias="meeting-db",
        db=meeting_db,
        host=db_uri.format(
            username=db_username, password=db_password, database=meeting_db
        ),
        uuidRepresentation="standard",
    )


def connect_to_auth_db():
    connect_to_db(
        db_uri.format(username=db_username, password=db_password, database=auth_db)
    )
