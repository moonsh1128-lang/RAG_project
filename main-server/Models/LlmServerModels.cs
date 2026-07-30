using System.Text.Json.Serialization;

namespace MainServer.Models;

// shared/schemas/main-llm
public sealed record LlmServerRequest(
    [property: JsonPropertyName("retrieved_content")] string RetrievedContent,
    [property: JsonPropertyName("question")] string Question);

public sealed record LlmServerResponse(
    [property: JsonPropertyName("result")] string Result);
