using System.Text.Json.Serialization;

namespace DbServer.Models;

// shared/schemas/main-db/message.request.schema.json, message.response.schema.json
public sealed record InsertMessageRequest(
    [property: JsonPropertyName("session_id")] string SessionId,
    [property: JsonPropertyName("sender_type")] string SenderType,
    [property: JsonPropertyName("message_text")] string MessageText);

public sealed record InsertMessageResponse(
    [property: JsonPropertyName("message_id")] string MessageId);
