using MainServer.Clients;
using MainServer.Models;
using Microsoft.AspNetCore.Mvc;

namespace MainServer.Controllers;

[ApiController]
[Route("complaint")]
public sealed class ComplaintController(LlmServerClient llmServer) : ControllerBase
{
    // rag_sources.py의 REAL_DATA_FILES와 같은 방식으로, 이 PC의 고정 경로를 그대로 씀.
    private const string TemplatePath = "/home/janghyeon/claude/rag-system/templates/고소장.md";

    [HttpPost]
    public async Task<ActionResult<ComplaintResponse>> PostAsync(ComplaintRequest request, CancellationToken ct)
    {
        var narrative = await llmServer.GenerateComplaintNarrativeAsync(request.Charge, request.IncidentDescription, ct);

        var evidenceList = request.Evidence.Count == 0
            ? "(제출할 증거자료 없음)"
            : string.Join("\n", request.Evidence.Select((item, i) => $"{i + 1}. {item}"));

        var template = await System.IO.File.ReadAllTextAsync(TemplatePath, ct);
        var document = template
            .Replace("{{고소인_명칭}}", request.ComplainantName)
            .Replace("{{고소인_대표자}}", request.ComplainantRepresentative ?? "")
            .Replace("{{고소인_주소}}", request.ComplainantAddress)
            .Replace("{{피고소인_성명}}", request.AccusedName)
            .Replace("{{피고소인_주소}}", request.AccusedAddress)
            .Replace("{{고소취지}}", narrative.Purpose)
            .Replace("{{고소사실}}", narrative.Facts)
            .Replace("{{증거물_목록}}", evidenceList)
            .Replace("{{제출일자}}", DateTime.Now.ToString("yyyy. M. d."))
            .Replace("{{제출처}}", request.SubmissionTarget);

        return Ok(new ComplaintResponse(document));
    }
}
