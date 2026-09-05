from typing import Optional
from arq import ArqRedis
from arq.jobs import Job, JobStatus


class TaskManager:
    """
    Durable TaskManager utilizing ARQ Redis pool for background job enqueuing,
    cancellation, and status monitoring.
    """
    def __init__(self, redis_pool: ArqRedis):
        self.redis_pool = redis_pool

    async def register_task(
        self,
        thread_id: str,
        payload: dict,
        user_fcm_token: Optional[str] = None
    ) -> None:
        await self.redis_pool.enqueue_job(
            "generate_paper_task",
            thread_id,
            payload,
            user_fcm_token,
            _job_id=thread_id
        )
        print(f"[INFO] Task for thread {thread_id} enqueued into ARQ Redis pool.")

    async def cancel_task(self, thread_id: str) -> bool:
        try:
            job = Job(job_id=thread_id, redis=self.redis_pool)
            success = await job.abort(timeout=10)
            print(f"[INFO] Aborted ARQ job for thread {thread_id}: {success}")
            return success
        except Exception as e:
            print(f"[WARN] Could not cancel task {thread_id}: {e}")
            return False

    async def is_running(self, thread_id: str) -> bool:
        try:
            job = Job(job_id=thread_id, redis=self.redis_pool)
            status = await job.status()
            return status in (JobStatus.queued, JobStatus.in_progress)
        except Exception as e:
            print(f"[WARN] Could not get status of task {thread_id}: {e}")
            return False

    async def register_resume_task(self, thread_id: str, selected_indices: list[int]) -> None:
        await self.redis_pool.enqueue_job(
            "resume_paper_task",
            thread_id,
            selected_indices,
            _job_id=f"{thread_id}-resume"
        )
        print(f"[INFO] Resume task for thread {thread_id} enqueued into ARQ Redis pool.")

