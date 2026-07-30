using DbServer.Data;
using DbServer.Models;
using Microsoft.AspNetCore.Mvc;

namespace DbServer.Controllers;

[ApiController]
[Route("messages")]
public sealed class MessagesController(LawLogRepository repository) : ControllerBase
{
    [HttpPost]
    public async Task<ActionResult<InsertMessageResponse>> PostAsync(InsertMessageRequest request, CancellationToken ct)
    {
        var messageId = await repository.InsertMessageAsync(
            request.SessionId, request.SenderType, request.MessageText, ct);
        return Ok(new InsertMessageResponse(messageId));
    }
}
