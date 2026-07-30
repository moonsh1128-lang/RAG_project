using System.Net.Http.Json;
using MainServer.Models;

namespace MainServer.Clients;

public sealed class RagServerClient(HttpClient http)
{
    public async Task<RagServerChunkResponse> SendChunkAsync(RagServerChunkRequest chunk, CancellationToken ct)
    {
        var response = await http.PostAsJsonAsync("/rag", chunk, ct);
        response.EnsureSuccessStatusCode();
        return (await response.Content.ReadFromJsonAsync<RagServerChunkResponse>(ct))!;
    }
}
