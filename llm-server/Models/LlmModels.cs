using System.Text.Json.Serialization;

namespace LlmServer.Models;

// shared/schemas/main-llm
public sealed record LlmRequest(
    [property: JsonPropertyName("retrieved_content")] string RetrievedContent,
    [property: JsonPropertyName("question")] string Question);

public sealed record LlmResponse(
    [property: JsonPropertyName("result")] string Result);

public sealed record ComplaintNarrativeRequest(
    [property: JsonPropertyName("charge")] string Charge,
    [property: JsonPropertyName("incident_description")] string IncidentDescription);

public sealed record ComplaintNarrativeResponse(
    [property: JsonPropertyName("purpose")] string Purpose,
    [property: JsonPropertyName("facts")] string Facts);

public sealed record HistoryTurn(
    [property: JsonPropertyName("question")] string Question,
    [property: JsonPropertyName("answer")] string Answer);

public sealed record RewriteRequest(
    [property: JsonPropertyName("history")] List<HistoryTurn> History,
    [property: JsonPropertyName("new_message")] string NewMessage);

public sealed record RewriteResponse(
    [property: JsonPropertyName("rewritten")] string Rewritten);
