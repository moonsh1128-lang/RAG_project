using System.Text.Json.Serialization;

namespace MainServer.Models;

// shared/schemas/main-rag — RagServer(Python)가 그대로 쓰는 필드명이라 대소문자를 그대로 맞춤. 청크 하나.
public sealed record RagServerChunkRequest(
    [property: JsonPropertyName("SessionId")] string SessionId,
    [property: JsonPropertyName("RagType")] string? RagType,
    [property: JsonPropertyName("RequestNumber")] int RequestNumber,
    [property: JsonPropertyName("FinalRequestNumber")] int? FinalRequestNumber,
    [property: JsonPropertyName("MessageChunk")] string MessageChunk,
    [property: JsonPropertyName("IsComplete")] bool IsComplete);

// IsFinal=false면 SelectRag/Message/RagContext/RetrievalTimeMs는 비어있다 (청크 ack).
public sealed record RagServerChunkResponse(
    [property: JsonPropertyName("IsFinal")] bool IsFinal,
    [property: JsonPropertyName("SelectRag")] string? SelectRag,
    [property: JsonPropertyName("message")] string? Message,
    [property: JsonPropertyName("RagContext")] string? RagContext,
    [property: JsonPropertyName("RetrievalTimeMs")] int? RetrievalTimeMs);
