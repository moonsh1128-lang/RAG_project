using DbServer.Data;
using DbServer.Models;
using Microsoft.AspNetCore.Mvc;

namespace DbServer.Controllers;

[ApiController]
[Route("rag-logs")]
public sealed class RagLogsController(LawLogRepository repository) : ControllerBase
{
    [HttpPost]
    public async Task<ActionResult<InsertRagLogResponse>> PostAsync(InsertRagLogRequest request, CancellationToken ct)
    {
        var logId = await repository.InsertRagLogAsync(
            request.MessageId, request.SearchQuery, request.TargetIndex,
            request.TopK, request.RetrievedChunks, request.RetrievalTimeMs, ct);
        return Ok(new InsertRagLogResponse(logId));
    }
}
