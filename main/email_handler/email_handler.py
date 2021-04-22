from fastapi import BackgroundTasks
from starlette.responses import JSONResponse
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import BaseModel, EmailStr, Field
from typing import List
import toml
from pathlib import Path

CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent.joinpath("auth/db-config.toml")
)
print("Using CONFIG_PATH:", CONFIG_PATH)

config = toml.load(str(CONFIG_PATH))


email_username = config["email-username"]
email_password = config["email-password"]
admin_email = config["admin-email"]

conf = ConnectionConfig(
    MAIL_USERNAME=email_username,
    MAIL_PASSWORD=email_password,
    MAIL_FROM=admin_email,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_TLS=True,
    MAIL_SSL=False,
)


class EmailSchema(BaseModel):
    receivers: List[EmailStr] = Field()
    subject: str = Field()
    body: str = Field()


async def email_handler(
    background_task: BackgroundTasks, email: EmailSchema
) -> JSONResponse:

    message = MessageSchema(
        subject=email.subject,
        recipients=email.receivers,  # List of recipients, as many as you can pass
        body=email.body,
        subtype="html",
    )

    fm = FastMail(conf)

    background_task.add_task(fm.send_message, message)

    return JSONResponse(status_code=200, content={"message": "email has been sent"})
