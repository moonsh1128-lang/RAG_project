using LlmServer.Clients;
using LlmServer.Models;
using Microsoft.AspNetCore.Mvc;

namespace LlmServer.Controllers;

[ApiController]
[Route("llm")]
public sealed class LlmController(OllamaClient ollama) : ControllerBase
{
    private const string SystemPrompt =
        "너는 민사법 관련 질문에 답하는 법률 보조 도우미다. 한국어로만 답한다. " +
        "사용자 메시지에 있는 [참고 정보]를 근거로 [질문]에 직접 답하라.";

    [HttpPost]
    public async Task<ActionResult<LlmResponse>> PostAsync(LlmRequest request, CancellationToken ct)
    {
        var userPrompt = $"[참고 정보]\n{request.RetrievedContent}\n\n[질문]\n{request.Question}\n\n위 참고 정보를 근거로 질문에 답하라.";
        var result = await ollama.ChatAsync(SystemPrompt, userPrompt, ct);
        return Ok(new LlmResponse(result));
    }
}
