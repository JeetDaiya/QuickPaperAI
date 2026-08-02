import json
from typing import TypedDict, Union
from upstash_redis.asyncio import Redis
from src.paper.models import ChapterStatus


class ChapterProgress(TypedDict):
    chapter: str
    status: str
    generated_count: int


class ProgressTracker:
    def __init__(self, redis_client: Redis, ttl_seconds: int):
        self.redis_client = redis_client
        self.ttl = ttl_seconds

    def _get_progress_key(self, thread_id: str) -> str:
        return f"progress:{thread_id}"

    def _get_cancel_key(self, thread_id: str) -> str:
        return f"cancel:{thread_id}"

    async def update_chapters_progress(
        self,
        thread_id: str,
        chapters: list[str],
        status: Union[ChapterStatus, str],
        generated_count: int = 0
    ) -> None:
        for chapter in chapters:
            await self.update_chapter_progress(
                thread_id=thread_id,
                chapter=chapter,
                status=status,
                generated_count=generated_count
            )

    async def update_chapter_progress(
        self,
        thread_id: str,
        chapter: str,
        status: Union[ChapterStatus, str],
        generated_count: int = 0
    ):
        key = self._get_progress_key(thread_id=thread_id)
        payload = {
            "chapter": str(chapter),
            "status": str(status.value if hasattr(status, "value") else status),
            "generated_count": int(generated_count)
        }

        try:
            await self.redis_client.hset(key=key, field=chapter, value=json.dumps(payload))
            await self.redis_client.expire(key=key, seconds=self.ttl)
        except Exception as e:
            print(f"Updating progress failed for {thread_id}, chapter {chapter}, {e}")

    async def get_chapter_progress(self, thread_id: str) -> dict[str, ChapterProgress]:
        key = self._get_progress_key(thread_id=thread_id)

        try:
            raw_data = await self.redis_client.hgetall(key)
            if not raw_data:
                return {}

            parsed_progress = {}
            for field, val in raw_data.items():
                parsed_progress[field] = json.loads(val)

            return parsed_progress
        except Exception as e:
            print(f"Fetching progress failed for {thread_id}, {e}")
            return {}

    async def delete_progress(self, thread_id: str):
        key = self._get_progress_key(thread_id=thread_id)

        try:
            await self.redis_client.delete(key)
        except Exception as e:
            print(f"Deleting progress failed for {thread_id}, {e}")

    async def mark_all_failed(self, thread_id: str):
        progress = await self.get_chapter_progress(thread_id)
        if progress:
            chapters = list(progress.keys())
            await self.update_chapters_progress(
                thread_id=thread_id,
                chapters=chapters,
                status=ChapterStatus.FAILED
            )

    async def mark_cancelled(self, thread_id: str):
        key = f"cancel:{thread_id}"
        await self.redis_client.set(key, "true", ex=3600)

    async def is_cancelled(self, thread_id: str) -> bool:
        key = self._get_cancel_key(thread_id=thread_id)
        val = await self.redis_client.get(key)
        return val is not None

