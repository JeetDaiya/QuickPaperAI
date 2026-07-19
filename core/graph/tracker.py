import json
from typing import TypedDict, Literal

from upstash_redis.asyncio import Redis


class ChapterProgress(TypedDict):
    chapter : str
    status : Literal["pending", "processing", "completed", "failed"]
    generated_count : int
    

class ProgressTracker:
    def __init__(self, redis_client: Redis, ttl_seconds: int):
        self.redis_client = redis_client
        self.ttl = ttl_seconds

    def _get_key(self, thread_id: str) -> str:
        return f"progress:{thread_id}"

    async def update_chapter_progress(self,thread_id: str, chapter : str, status : Literal["pending", "processing", "completed", "failed"], generated_count : int = 0):

        key = self._get_key(thread_id=thread_id)
        payload = {
            "chapter": str(chapter),
            "status": str(status),
            "generated_count": int(generated_count)
        }

        try:
            await self.redis_client.hset(key=key, field=chapter, value=json.dumps(payload))
            await self.redis_client.expire(key=key, seconds=self.ttl)
        except Exception as e:
            print(f"Updating progress failed for ${thread_id}, chapter ${chapter}, {e}")

    async  def get_chapter_progress(self, thread_id: str) -> dict[str, ChapterProgress]:
        key = self._get_key(thread_id=thread_id)

        try:
            raw_data = await self.redis_client.hgetall(key)
            if not raw_data:
                return {}

            parsed_progress = {}

            for field, val in raw_data.items():
                parsed_progress[field] = json.loads(val)

            return parsed_progress
        except Exception as e:
            print(f"Fetching progress failed for ${thread_id}, {e}")
            return {}

    async def delete_progress(self, thread_id: str):
        key = self._get_key(thread_id=thread_id)

        try:
            await self.redis_client.delete(key)
        except Exception as e:
            print(f"Deleting progress failed for ${thread_id}, {e}")


