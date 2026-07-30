using System.Text.Json.Serialization;

namespace MainServer.Models;

// api-main / client-api 스키마 (shared/schemas/api-main) — 청크 하나
public sealed record QueryChunkRequest(
    [property: JsonPropertyName("session_id")] string SessionId,
    [property: JsonPropertyName("rag_selector_query")] string? RagSelectorQuery,
    [property: JsonPropertyName("request_number")] int RequestNumber,
    [property: JsonPropertyName("final_request_number")] int? FinalRequestNumber,
    [property: JsonPropertyName("message_chunk")] string MessageChunk,
    [property: JsonPropertyName("is_complete")] bool IsComplete);

public sealed record ChunkAckResponse(
    [property: JsonPropertyName("chunk_received")] bool ChunkReceived,
    [property: JsonPropertyName("request_number")] int RequestNumber);
