using System.Text.Json.Serialization;

namespace MainServer.Models;

// shared/schemas/main-db
public sealed record EnsureSessionRequest(
    [property: JsonPropertyName("session_id")] string SessionId,
    [property: JsonPropertyName("user_id")] string? UserId,
    [property: JsonPropertyName("title")] string? Title);

public sealed record InsertMessageRequest(
    [property: JsonPropertyName("session_id")] string SessionId,
    [property: JsonPropertyName("sender_type")] string SenderType,
    [property: JsonPropertyName("message_text")] string MessageText);

public sealed record InsertMessageResponse(
    [property: JsonPropertyName("message_id")] string MessageId);

public sealed record InsertRagLogRequest(
    [property: JsonPropertyName("message_id")] string MessageId,
    [property: JsonPropertyName("search_query")] string SearchQuery,
    [property: JsonPropertyName("target_index")] string TargetIndex,
    [property: JsonPropertyName("top_k")] int TopK,
    [property: JsonPropertyName("retrieved_chunks")] string RetrievedChunks,
    [property: JsonPropertyName("retrieval_time_ms")] int? RetrievalTimeMs);
