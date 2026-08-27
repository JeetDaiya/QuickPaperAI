from typing import Optional

from src.notifications.adapters.firebase_notification_service import FirebaseNotificationService
from src.paper.graph.runner import run_graph
from src.paper.models import PaperRequest, ChapterStatus
from src.paper.graph.state import PaperState
from src.paper.graph.config import GraphConfig
from src.notifications.constants.notification_messages import NotificationMessages


async def generate_paper_task(
    ctx: dict,
    thread_id: str,
    paper_request_dict: dict,
    user_fcm_token: Optional[str] = None
):
    """
    ARQ Background Task Runner for Paper Generation.
    Executes or resumes LangGraph paper generation with PostgreSQL checkpoints.
    """
    agent = ctx["agent"]
    progress_tracker = ctx["progress_tracker"]
    notification_service  : Optional[FirebaseNotificationService] = ctx.get("notification_service")

    # Reconstruct Pydantic domain model from dictionary payload
    paper_request = PaperRequest(**paper_request_dict)

    # Construct graph execution dependencies
    dependencies = GraphConfig(
        chunk_repo=ctx["chunk_repo"],
        html_paper_formatter=ctx["html_paper_formatter"],
        markdown_paper_formatter=ctx["markdown_paper_formatter"],
        document_compiler=ctx["document_compiler"],
        progress_tracker=progress_tracker
    )

    try:
        # Check if a checkpoint state already exists in PostgreSQL
        snapshot = await agent.aget_state({"configurable": {"thread_id": thread_id}})
        is_resume = bool(snapshot and snapshot.values)

        if is_resume:
            print(f"[INFO] Resuming paper generation for thread {thread_id} from PostgreSQL checkpoint...")
            await run_graph(agent, paper_state=None, dependencies=dependencies, thread_id=thread_id)
        else:
            print(f"[INFO] Starting fresh paper generation for thread {thread_id}...")
            initial_state: PaperState = {
                "all_questions": [],
                "selected_questions": [],
                "paper_request": paper_request,
                "thread_id": thread_id
            }
            await run_graph(agent, paper_state=initial_state, dependencies=dependencies, thread_id=thread_id)

        print(f"[INFO] run_graph execution finished for thread {thread_id}")

        # Inspect graph snapshot to detect if review_node interrupt was reached
        post_run_snapshot = await agent.aget_state({"configurable": {"thread_id": thread_id}})
        has_interrupts = bool(post_run_snapshot.tasks and post_run_snapshot.tasks[0].interrupts)

        if has_interrupts:
            questions = post_run_snapshot.tasks[0].interrupts[0].value.get("questions", [])
            if notification_service and user_fcm_token:
                print(f"[INFO] Dispatching FCM Review Ready Push Notification for thread {thread_id}...")
                await notification_service.send_notification(
                    thread_id=thread_id,
                    token=user_fcm_token,
                    message=NotificationMessages.format_paper_review_ready_body(
                        institution_name=paper_request.institution_name,
                        question_count=len(questions),
                        subject=paper_request.subject,
                        standard=paper_request.standard,
                    ),
                    title=NotificationMessages.PAPER_REVIEW_READY_TITLE
                )

    except Exception as e:
        current_try = ctx.get("job_try", 1)
        max_tries = 3
        print(f"[ERROR] generate_paper_task try {current_try}/{max_tries} failed for thread {thread_id}: {e}")

        # On the FINAL failed retry attempt:
        if current_try >= max_tries:
            # 1. Update progress tracker status in Redis to FAILED
            if progress_tracker:
                await progress_tracker.update_chapters_progress(
                    thread_id=thread_id,
                    chapters=paper_request.chapters,
                    status=ChapterStatus.FAILED
                )

            paper_repo = ctx.get("paper_repo")
            if paper_repo:
                try:
                    from src.db.records.paper_record import PaperRecord, Status
                    record = PaperRecord(
                        thread_id=thread_id,
                        user_id="",
                        status=Status.FAILED
                    )
                    paper_repo.update_paper_session(thread_id=thread_id, paper_record=record)
                except Exception as repo_err:
                    print(f"[WARN] Failed to update paper session status in DB to FAILED: {repo_err}")

            # 2. Dispatch FCM Failure Push Notification
            if notification_service and user_fcm_token:
                await notification_service.send_notification(
                    thread_id=thread_id,
                    token=user_fcm_token,
                    message=NotificationMessages.format_paper_failed_body(
                        institution_name=paper_request.institution_name
                    ),
                    title=NotificationMessages.PAPER_FAILED_TITLE
                )

        # Re-raise so ARQ registers retry or records job failure
        raise e
