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
builder.Services.AddHttpClient<RagServerClient>(client =>
{
    client.BaseAddress = new Uri(Environment.GetEnvironmentVariable("RAG_SERVER_URL") ?? "http://localhost:8001");
});
builder.Services.AddHttpClient<LlmServerClient>(client =>
{
    client.BaseAddress = new Uri(Environment.GetEnvironmentVariable("LLM_SERVER_URL") ?? "http://localhost:8002");
});
builder.Services.AddHttpClient<DbServerClient>(client =>
{
    client.BaseAddress = new Uri(Environment.GetEnvironmentVariable("DB_SERVER_URL") ?? "http://localhost:8003");
});

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseAuthorization();

app.MapControllers();

app.Run();
