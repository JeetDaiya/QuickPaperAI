from functools import lru_cache


@lru_cache
def get_email_service():
    from src.mail.adapters.fastmail_mailer import FastMailService
    return FastMailService()
