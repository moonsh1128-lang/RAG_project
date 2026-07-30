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
