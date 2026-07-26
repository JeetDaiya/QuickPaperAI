"""
Centralized Notification Messages & Templates for QuickPaper AI.
"""


class NotificationMessages:
    PAPER_REVIEW_READY_TITLE = "📝 Questions Ready for Review!"
    
    PAPER_FAILED_TITLE = "⚠️ Paper Generation Failed"
    
    WELCOME_TITLE = "👋 Welcome to QuickPaper AI!"
    WELCOME_BODY = "Push notifications enabled. We will alert you when your questions are ready for review."

    @staticmethod
    def format_paper_review_ready_body(institution_name: str = "", subject: str = "", standard: str = "", question_count: int = 0) -> str:
        details = f" ({subject.upper()} Std {standard})" if subject and standard else ""
        count_str = f"{question_count} questions generated" if question_count > 0 else "Questions generated"
        return f"{count_str} for '{institution_name}'{details}. Tap to review and select questions for your paper."

    @staticmethod
    def format_paper_review_url(thread_id: str) -> str:
        return f"/papers/{thread_id}/review"

    @staticmethod
    def format_paper_failed_body(institution_name: str) -> str:
        return f"We encountered an issue generating questions for '{institution_name}'. Please try again."
