class GeneratedPapers:
    TABLE = "generated_papers"

    THREAD_ID = "thread_id"
    USER_ID = "user_id"
    INSTITUTION_NAME = "institution_name"
    SUBJECT = "subject"
    STANDARD = "standard"
    CHAPTERS = "chapters"
    DIFFICULTY = "difficulty"
    OBJECTIVE_COUNT = "objective_count"
    SUBJECTIVE_COUNT = "subjective_count"
    ALLOWED_TYPES = "allowed_types"
    PAPER_PDF_PATH = "paper_pdf_path"
    PAPER_DOCX_PATH = "paper_docx_path"
    ANSWER_PDF_PATH = "answer_pdf_path"
    STATUS = "status"
    DIFFICULTY_DISTRIBUTION = "difficulty_distribution"
    CREATED_AT = "created_at"


class Chunks:
    TABLE = "chunks"

    STANDARD = "standard"
    SUBJECT = "subject"
    CHAPTER_NAME = "chapter_name"
    SUB_TOPIC = "sub_topic"
    CHUNK_INDEX = "chunk_index"

class User:
    TABLE = "users"

    NOTIFICATIONS_ENABLED = "notifications_enabled"
    FCM_TOKEN = "fcm_token"
    IS_ACTIVE = "is_active"
    HASHED_PASSWORD = "hashed_password"
    EMAIL = "email"
    USER_ID = "user_id"
    NAME = "name"
