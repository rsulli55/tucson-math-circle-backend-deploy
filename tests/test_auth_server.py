from fastapi.testclient import TestClient
import toml

# hack to add project directory to path and make modules work nicely
import sys
from pathlib import Path

PROJECTS_DIR = Path(__file__).resolve().parents[2]
print("Appending PROJECTS_DIR to PATH:", PROJECTS_DIR)
sys.path.append(str(PROJECTS_DIR))

from backend.auth.main import app
from backend.auth.db.main import connect_to_db

# get the config file path
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

client = TestClient(app)


def test_admin_login():
    response = client.post(
        "/token", data={"username": "admin@email.com", "password": "password"}
    )
    assert response.status_code == 200
    json = response.json()
    assert "access_token" in json
    assert json["token_type"] == "bearer"


def test_student_login():
    response = client.post(
        "/token", data={"username": "student@email.com", "password": "password"}
    )
    assert response.status_code == 200
    json = response.json()
    assert "access_token" in json
    assert json["token_type"] == "bearer"


# check that duplicate emails cannot be registered
def test_student_register_already_exists():
    response = client.post(
        "/student/register",
        json={"email": "student@email.com", "role": "student", "password": "password"},
    )
    assert response.status_code == 400
    json = response.json()
    assert json["detail"] == "User already exists"


def test_student_update_email():
    response = client.post(
        "/token", data={"username": "student2@email.com", "password": "password"}
    )
    assert response.status_code == 200
    json = response.json()
    access_token = json["access_token"]
    # change email
    response = client.put(
        "/student/update_email",
        json={"email": "student2testing111@email.com"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    json = response.json()
    assert response.status_code == 200
    assert json["email"] == "student2testing111@email.com"
    # change it back
    response = client.put(
        "/student/update_email",
        json={"email": "student2@email.com"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    json = response.json()
    assert response.status_code == 200
    assert json["email"] == "student2@email.com"


def test_student_update_password():
    response = client.post(
        "/token", data={"username": "student2@email.com", "password": "password"}
    )
    assert response.status_code == 200
    json = response.json()
    access_token = json["access_token"]
    # change email
    response = client.put(
        "/student/update_password",
        json={"password": "password"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200


def test_admin_me():
    response = client.post(
        "/token", data={"username": "admin@email.com", "password": "password"}
    )
    assert response.status_code == 200
    json = response.json()
    access_token = json["access_token"]
    response = client.get(
        "/admin/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    json = response.json()
    assert response.status_code == 200
    assert json["email"] == "admin@email.com"
    assert json["role"] == "admin"


def test_student_me():
    response = client.post(
        "/token", data={"username": "student2@email.com", "password": "password"}
    )
    assert response.status_code == 200
    json = response.json()
    access_token = json["access_token"]
    response = client.get(
        "/student/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    json = response.json()
    assert response.status_code == 200
    assert json["email"] == "student2@email.com"
    assert json["role"] == "student"
