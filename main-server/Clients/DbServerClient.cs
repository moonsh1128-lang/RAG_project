using System.Net.Http.Json;
using MainServer.Models;

namespace MainServer.Clients;

public sealed class DbServerClient(HttpClient http)
{
    public async Task EnsureSessionAsync(string sessionId, CancellationToken ct)
    {
        var response = await http.PostAsJsonAsync(
            "/sessions/ensure", new EnsureSessionRequest(sessionId, UserId: null, Title: null), ct);
        response.EnsureSuccessStatusCode();
    }

    public async Task<string> InsertMessageAsync(
        string sessionId, string senderType, string messageText, CancellationToken ct)
    {
        var response = await http.PostAsJsonAsync(
            "/messages", new InsertMessageRequest(sessionId, senderType, messageText), ct);
        response.EnsureSuccessStatusCode();
        var body = await response.Content.ReadFromJsonAsync<InsertMessageResponse>(ct);
        return body!.MessageId;
    }

    public async Task InsertRagLogAsync(
        string messageId, string searchQuery, string targetIndex, int topK, string retrievedChunks,
        int retrievalTimeMs, CancellationToken ct)
    {
        var response = await http.PostAsJsonAsync(
            "/rag-logs",
            new InsertRagLogRequest(messageId, searchQuery, targetIndex, topK, retrievedChunks, retrievalTimeMs),
            ct);
        response.EnsureSuccessStatusCode();
    }
}
