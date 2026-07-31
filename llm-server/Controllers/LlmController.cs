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
        "사용자 메시지에 있는 [참고 정보]를 근거로 [질문]에 직접 답하라. " +
        "답변은 마크다운 형식으로 작성한다 — 필요하면 소제목(##)과 목록(-)을 쓰고, " +
        "핵심 결론이나 인용한 법 조문·판례명은 **굵게** 표시한다.";

    [HttpPost]
    public async Task<ActionResult<LlmResponse>> PostAsync(LlmRequest request, CancellationToken ct)
    {
        var userPrompt = $"[참고 정보]\n{request.RetrievedContent}\n\n[질문]\n{request.Question}\n\n위 참고 정보를 근거로 질문에 답하라.";
        var result = await ollama.ChatAsync(SystemPrompt, userPrompt, ct);
        return Ok(new LlmResponse(result));
    }

    private const string ComplaintSystemPrompt =
        "너는 고소장 작성을 돕는 법률 보조 도우미다. 한국어로만 답한다. " +
        "사용자가 제공한 [죄명]과 [사건 설명]만 근거로 삼아라 — 사용자가 말하지 않은 사실이나 " +
        "숫자, 날짜, 인물을 지어내지 마라. 아래 두 항목을 아래 형식 그대로 정확히 지켜서 작성하라.\n\n" +
        "[고소취지]\n(피고소인의 행위와 그로 인한 결과를 한두 문장으로 요약)\n\n" +
        "[고소사실]\n(사건 경위, 피고소인의 구체적 행위, 고소인이 입은 피해를 시간 순서대로 서술)";

    [HttpPost("narrative")]
    public async Task<ActionResult<ComplaintNarrativeResponse>> PostNarrativeAsync(
        ComplaintNarrativeRequest request, CancellationToken ct)
    {
        var userPrompt = $"[죄명]\n{request.Charge}\n\n[사건 설명]\n{request.IncidentDescription}";
        var raw = await ollama.ChatAsync(ComplaintSystemPrompt, userPrompt, ct);
        return Ok(ParseNarrative(raw));
    }

    private static ComplaintNarrativeResponse ParseNarrative(string raw)
    {
        const string purposeMarker = "[고소취지]";
        const string factsMarker = "[고소사실]";

        var purposeIndex = raw.IndexOf(purposeMarker, StringComparison.Ordinal);
        var factsIndex = raw.IndexOf(factsMarker, StringComparison.Ordinal);

        // 모델이 형식을 어기면(마커 누락) 전체를 고소사실 쪽에 넣고 고소취지는 비워둔다 —
        // 사용자가 나중에 직접 채울 수 있도록 빈 문자열로만 두고, 내용을 지어내 채우지 않는다.
        if (purposeIndex < 0 || factsIndex < 0 || factsIndex <= purposeIndex)
        {
            return new ComplaintNarrativeResponse(Purpose: "", Facts: raw.Trim());
        }

        var purpose = raw[(purposeIndex + purposeMarker.Length)..factsIndex].Trim();
        var facts = raw[(factsIndex + factsMarker.Length)..].Trim();
        return new ComplaintNarrativeResponse(purpose, facts);
    }
}
