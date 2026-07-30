using MainServer.Clients;
using MainServer.Services;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.

builder.Services.AddControllers();
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

// 청크로 나뉘어 들어오는 질문을 session_id 기준으로 재조립하는 저장소 (DB엔 완성된 텍스트로 저장하기 위함)
builder.Services.AddSingleton<ChunkAssemblyStore>();

// 다운스트림 서버 주소는 환경변수로 지정 (RagServer가 OLLAMA_HOST를 읽는 것과 같은 방식)
// Timeout을 명시하지 않으면 HttpClient 기본값(100초)에 암묵적으로 의존하게 되어 장애 시 원인 파악이 어려움 — 명시적으로 지정.
builder.Services.AddHttpClient<RagServerClient>(client =>
{
    client.BaseAddress = new Uri(Environment.GetEnvironmentVariable("RAG_SERVER_URL") ?? "http://localhost:8001");
    client.Timeout = TimeSpan.FromSeconds(30);
});
builder.Services.AddHttpClient<LlmServerClient>(client =>
{
    client.BaseAddress = new Uri(Environment.GetEnvironmentVariable("LLM_SERVER_URL") ?? "http://localhost:8002");
    // LlmServer 자신도 Ollama 호출에 120초 Timeout을 걸어두므로, 그보다 여유를 두어 LlmServer가 먼저 정리할 시간을 준다.
    client.Timeout = TimeSpan.FromSeconds(150);
});
builder.Services.AddHttpClient<DbServerClient>(client =>
{
    client.BaseAddress = new Uri(Environment.GetEnvironmentVariable("DB_SERVER_URL") ?? "http://localhost:8003");
    client.Timeout = TimeSpan.FromSeconds(15);
});

var app = builder.Build();

// 다운스트림 HttpClient.Timeout으로 인한 취소(OperationCanceledException)나 다운스트림이 이미
// 504/5xx를 응답한 경우(EnsureSuccessStatusCode가 던지는 HttpRequestException)를 원인 불명의
// 500 대신 504로 명확히 응답. RequestAborted가 이미 켜져 있으면 호출자가 먼저 끊은 것이므로 응답을 시도하지 않는다.
app.Use(async (context, next) =>
{
    try
    {
        await next();
    }
    catch (Exception ex) when (
        (ex is OperationCanceledException or HttpRequestException) && !context.RequestAborted.IsCancellationRequested)
    {
        context.Response.StatusCode = StatusCodes.Status504GatewayTimeout;
        await context.Response.WriteAsJsonAsync(new { error = "다운스트림 서버 응답 시간 초과" });
    }
});

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseAuthorization();

app.MapControllers();

app.Run();
