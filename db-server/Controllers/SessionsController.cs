using DbServer.Data;
using DbServer.Models;
using Microsoft.AspNetCore.Mvc;

namespace DbServer.Controllers;

[ApiController]
[Route("sessions")]
public sealed class SessionsController(LawLogRepository repository) : ControllerBase
{
    [HttpPost("ensure")]
    public async Task<IActionResult> EnsureAsync(EnsureSessionRequest request, CancellationToken ct)
    {
        await repository.EnsureSessionAsync(request.SessionId, request.UserId, request.Title, ct);
        return Ok();
    }
}
