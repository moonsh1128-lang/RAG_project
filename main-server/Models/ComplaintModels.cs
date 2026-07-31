using System.Text.Json.Serialization;

namespace MainServer.Models;

public sealed record ComplaintRequest(
    [property: JsonPropertyName("complainant_name")] string ComplainantName,
    [property: JsonPropertyName("complainant_representative")] string? ComplainantRepresentative,
    [property: JsonPropertyName("complainant_address")] string ComplainantAddress,
    [property: JsonPropertyName("accused_name")] string AccusedName,
    [property: JsonPropertyName("accused_address")] string AccusedAddress,
    [property: JsonPropertyName("charge")] string Charge,
    [property: JsonPropertyName("incident_description")] string IncidentDescription);

public sealed record ComplaintResponse(
    [property: JsonPropertyName("document")] string Document);
