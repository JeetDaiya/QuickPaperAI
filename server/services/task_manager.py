import asyncio


class TaskManager:
    def __init__(self):
        self._running_tasks : dict[str, asyncio.Task] = dict()

    def register_task(self, thread_id: str, task: asyncio.Task):
        self._running_tasks[thread_id] = task
        task.add_done_callback(lambda t: self._running_tasks.pop(thread_id))

    def cancel_task(self, thread_id: str):
        if thread_id in self._running_tasks:
            task = self._running_tasks.pop(thread_id)
            if not task.done():
                task.cancel()
                print(f"Cancelled active background task: {thread_id}")
            self._running_tasks.pop(thread_id)

    def is_running(self, thread_id: str) -> bool:
        task = self._running_tasks.get(thread_id)
        return task is not None and not task.done()