var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

// Liveness only says the process runs. Readiness (relaying the RAG service) and /api/ask
// are added together with the typed RAG client.
app.MapGet("/health/live", () => Results.Ok(new { status = "live" }));

app.Run();
