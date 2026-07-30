import asyncio
from typing import Awaitable, Callable


class JsonMessageChannel:
    """동시에 여러 요청이 들어와도 handler는 먼저 들어온 순서대로 하나씩만 실행한다."""

    def __init__(self, handler: Callable[[dict], Awaitable[dict]]):
        self._queue: asyncio.Queue[tuple[dict, asyncio.Future]] = asyncio.Queue()
        self._handler = handler
        self._worker_task: asyncio.Task | None = None

    def start(self) -> None:
        self._worker_task = asyncio.create_task(self._run())

    async def submit(self, payload: dict) -> dict:
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        await self._queue.put((payload, future))
        return await future

    async def _run(self) -> None:
        while True:
            payload, future = await self._queue.get()
            try:
                result = await self._handler(payload)
                future.set_result(result)
            except Exception as exc:
                future.set_exception(exc)
            finally:
                self._queue.task_done()
