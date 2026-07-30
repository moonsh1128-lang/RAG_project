"""청크(조각)로 나뉘어 들어오는 요청을 session_id 기준으로 모아 완성 여부를 판단한다."""


class ChunkAssembly:
    def __init__(self):
        self._chunks: dict[int, str] = {}
        self._final_request_number: int | None = None

    def add(self, request_number: int, message_chunk: str, final_request_number: int | None) -> None:
        self._chunks[request_number] = message_chunk
        if final_request_number is not None:
            self._final_request_number = final_request_number

    def is_ready(self, is_complete: bool) -> bool:
        if not is_complete or self._final_request_number is None:
            return False
        # 1..final_request_number까지 빠진 번호가 없어야 완성으로 본다
        return all(i in self._chunks for i in range(1, self._final_request_number + 1))

    def assemble(self) -> str:
        return "".join(self._chunks[i] for i in range(1, self._final_request_number + 1))
