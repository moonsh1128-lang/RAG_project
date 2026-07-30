using System.Text.Json.Serialization;

namespace DbServer.Models;

// shared/schemas/main-db/rag-log.request.schema.json, rag-log.response.schema.json
public sealed record InsertRagLogRequest(
    [property: JsonPropertyName("message_id")] string MessageId,
    [property: JsonPropertyName("search_query")] string SearchQuery,
    [property: JsonPropertyName("target_index")] string TargetIndex,
    [property: JsonPropertyName("top_k")] int TopK,
    [property: JsonPropertyName("retrieved_chunks")] string RetrievedChunks,
    [property: JsonPropertyName("retrieval_time_ms")] int? RetrievalTimeMs);

public sealed record InsertRagLogResponse(
    [property: JsonPropertyName("log_id")] string LogId);
