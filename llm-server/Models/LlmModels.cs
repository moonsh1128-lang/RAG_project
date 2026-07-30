using System.Text.Json.Serialization;

namespace LlmServer.Models;

// shared/schemas/main-llm
public sealed record LlmRequest(
    [property: JsonPropertyName("retrieved_content")] string RetrievedContent,
    [property: JsonPropertyName("question")] string Question);

public sealed record LlmResponse(
    [property: JsonPropertyName("result")] string Result);
