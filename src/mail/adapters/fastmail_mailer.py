from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from src.mail.interfaces.interface import EmailService

from src.config import model_settings


class FastMailService(EmailService):
    def __init__(self):
        self.connection_config =  ConnectionConfig(
            MAIL_FROM=model_settings.MAIL_FROM,
            MAIL_USERNAME=model_settings.MAIL_USERNAME,
            MAIL_PASSWORD=model_settings.MAIL_PASSWORD,
            MAIL_PORT=587,
            MAIL_SERVER="smtp-relay.brevo.com",
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )

        self.fastMail = FastMail(self.connection_config)

    async def send_email(self, recipient: str, subject: str, body: str):
        try:
            message = MessageSchema(
                subject=subject,
                recipients=[recipient],
                body=body,
                subtype=MessageType.html
            )

            await self.fastMail.send_message(message)
        except Exception as e:
            raise e