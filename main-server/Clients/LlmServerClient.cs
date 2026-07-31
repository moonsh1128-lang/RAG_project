using System.Net.Http.Json;
using MainServer.Models;

namespace MainServer.Clients;

public sealed class LlmServerClient(HttpClient http)
{
    public async Task<LlmServerResponse> ExecuteAsync(
        string retrievedContent, string question, CancellationToken ct)
    {
        var response = await http.PostAsJsonAsync(
            "/llm", new LlmServerRequest(retrievedContent, question), ct);
        response.EnsureSuccessStatusCode();
        return (await response.Content.ReadFromJsonAsync<LlmServerResponse>(ct))!;
    }

    public async Task<ComplaintNarrativeResponse> GenerateComplaintNarrativeAsync(
        string charge, string incidentDescription, CancellationToken ct)
    {
        var response = await http.PostAsJsonAsync(
            "/llm/narrative", new ComplaintNarrativeRequest(charge, incidentDescription), ct);
        response.EnsureSuccessStatusCode();
        return (await response.Content.ReadFromJsonAsync<ComplaintNarrativeResponse>(ct))!;
    }
}
