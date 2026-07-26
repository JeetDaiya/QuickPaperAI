import firebase_admin
from firebase_admin import credentials, messaging
from src.base_settings import settings


class FirebaseNotificationService:
    def __init__(self):
        self.cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
        self.firebase_app = firebase_admin.initialize_app(self.cred)

    async def send_notification(self, thread_id: str, message: str, title: str, token: str):
        preview_path = self._build_preview_url(thread_id=thread_id)
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:8080").rstrip("/")
        full_url = f"{frontend_url}{preview_path}"

        try:
            webpush_kwargs = {}
            if full_url.startswith("https://"):
                webpush_kwargs["fcm_options"] = messaging.WebpushFCMOptions(link=full_url)

            message_payload = messaging.Message(
                notification=messaging.Notification(
                    body=message,
                    title=title,
                ),
                token=token,
                data={
                    "thread_id": thread_id,
                    "action": "open_preview",
                    "url": preview_path,
                    "full_url": full_url
                },
                webpush=messaging.WebpushConfig(**webpush_kwargs) if webpush_kwargs else None
            )
            
            messaging.send(message_payload)
            print(f"[INFO] FCM notification sent successfully for thread {thread_id}")
            return True
        except Exception as e:
            print(f"[ERROR] Error sending FCM notification: {e}")
            return False

    @staticmethod
    def _build_preview_url(thread_id: str):
        return f"/papers/{thread_id}/review"
