using System.Text.Json.Serialization;

namespace DbServer.Models;

// shared/schemas/main-db/session-ensure.request.schema.json
public sealed record EnsureSessionRequest(
    [property: JsonPropertyName("session_id")] string SessionId,
    [property: JsonPropertyName("user_id")] string? UserId,
    [property: JsonPropertyName("title")] string? Title);
