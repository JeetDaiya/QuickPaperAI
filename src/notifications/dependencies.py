from functools import lru_cache

from src.notifications.adapters.firebase_notification_service import FirebaseNotificationService


@lru_cache
def get_notification_service() -> FirebaseNotificationService:
    return FirebaseNotificationService()
