using LlmServer.Clients;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.

builder.Services.AddControllers();
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

var chatModel = Environment.GetEnvironmentVariable("OLLAMA_CHAT_MODEL") ?? "llama3.2:3b";
builder.Services.AddHttpClient("ollama", client =>
{
    client.BaseAddress = new Uri(Environment.GetEnvironmentVariable("OLLAMA_HOST") ?? "http://localhost:11434");
    client.Timeout = TimeSpan.FromSeconds(120);
}).AddTypedClient((http, _) => new OllamaClient(http, chatModel));

var app = builder.Build();

// Ollama 호출의 HttpClient.Timeout(120초)으로 인한 취소를 원인 불명의 500 대신 504로 명확히 응답.
// RequestAborted가 이미 켜져 있으면 호출자(클라이언트)가 먼저 끊은 것이므로 응답을 시도하지 않는다.
app.Use(async (context, next) =>
{
    try
    {
        await next();
    }
    catch (OperationCanceledException) when (!context.RequestAborted.IsCancellationRequested)
    {
        context.Response.StatusCode = StatusCodes.Status504GatewayTimeout;
        await context.Response.WriteAsJsonAsync(new { error = "Ollama 응답 시간 초과" });
    }
});

// 이 PC의 Ollama에서 생성 모델이 실제로 있는지 시작 시점에 확인
using (var scope = app.Services.CreateScope())
{
    var ollama = scope.ServiceProvider.GetRequiredService<OllamaClient>();
    await ollama.EnsureChatModelAvailableAsync(CancellationToken.None);
}

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseAuthorization();

app.MapControllers();

app.Run();
