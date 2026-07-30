using System.Net.Http.Json;
using System.Text.Json.Nodes;

namespace LlmServer.Clients;

public sealed class OllamaClient(HttpClient http, string chatModel)
{
    public async Task<List<string>> ListModelsAsync(CancellationToken ct)
    {
        var response = await http.GetAsync("/api/tags", ct);
        response.EnsureSuccessStatusCode();
        var body = await response.Content.ReadFromJsonAsync<JsonNode>(cancellationToken: ct);
        return body!["models"]!.AsArray()
            .Select(m => m!["name"]!.GetValue<string>())
            .ToList();
    }

    public async Task EnsureChatModelAvailableAsync(CancellationToken ct)
    {
        var models = await ListModelsAsync(ct);
        if (!models.Any(m => m == chatModel || m.StartsWith($"{chatModel}:")))
        {
            throw new InvalidOperationException(
                $"Ollama({http.BaseAddress})에 생성 모델 '{chatModel}'이 없음. 설치된 모델: {string.Join(", ", models)}");
        }
    }

    public async Task<string> ChatAsync(string systemPrompt, string userPrompt, CancellationToken ct)
    {
        var request = new JsonObject
        {
            ["model"] = chatModel,
            ["stream"] = false,
            ["messages"] = new JsonArray
            {
                new JsonObject { ["role"] = "system", ["content"] = systemPrompt },
                new JsonObject { ["role"] = "user", ["content"] = userPrompt },
            },
            ["options"] = new JsonObject { ["temperature"] = 0 },
        };

        var response = await http.PostAsJsonAsync("/api/chat", request, ct);
        response.EnsureSuccessStatusCode();
        var body = await response.Content.ReadFromJsonAsync<JsonNode>(cancellationToken: ct);
        return body!["message"]!["content"]!.GetValue<string>().Trim();
    }
}
