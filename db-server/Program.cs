using DbServer.Data;
using MySqlConnector;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.

builder.Services.AddControllers();
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

string RequireEnv(string name) =>
    Environment.GetEnvironmentVariable(name)
    ?? throw new InvalidOperationException($"환경변수 {name}이(가) 설정되지 않음");

var connectionStringBuilder = new MySqlConnectionStringBuilder
{
    Server = RequireEnv("DB_HOST"),
    UserID = RequireEnv("DB_USER"),
    Password = RequireEnv("DB_PASSWORD"),
    Database = RequireEnv("DB_NAME"),
};
builder.Services.AddSingleton(new LawLogRepository(connectionStringBuilder.ConnectionString));

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseAuthorization();

app.MapControllers();

app.Run();
