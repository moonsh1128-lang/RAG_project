using System.Text.Json.Serialization;

namespace MainServer.Models;

// api-main / client-api 스키마 (shared/schemas/api-main) — 청크 하나
public sealed record QueryChunkRequest(
    [property: JsonPropertyName("session_id")] string SessionId,
    [property: JsonPropertyName("rag_selector_query")] string? RagSelectorQuery,
    [property: JsonPropertyName("request_number")] int RequestNumber,
    [property: JsonPropertyName("final_request_number")] int? FinalRequestNumber,
    [property: JsonPropertyName("message_chunk")] string MessageChunk,
    [property: JsonPropertyName("is_complete")] bool IsComplete,
    // 아래 둘은 1번 청크에만 실림 — Client가 세션 동안 메모리에 들고 있는 대화 턴 수/이전 대화.
    [property: JsonPropertyName("message_count")] int? MessageCount = null,
    [property: JsonPropertyName("history")] List<HistoryTurn>? History = null);

public sealed record HistoryTurn(
    [property: JsonPropertyName("question")] string Question,
    [property: JsonPropertyName("answer")] string Answer);

public sealed record ChunkAckResponse(
    [property: JsonPropertyName("chunk_received")] bool ChunkReceived,
    [property: JsonPropertyName("request_number")] int RequestNumber);
