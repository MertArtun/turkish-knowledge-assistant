using SupportAssistant.Api;

var builder = WebApplication.CreateBuilder(args);

// /api/ask is the only endpoint that reads a body, so one server-wide limit is enough.
builder.WebHost.ConfigureKestrel(kestrel => kestrel.Limits.MaxRequestBodySize = AskEndpoint.MaxBodyBytes);

builder.Services.AddSingleton(services => RagSettings.Load(services.GetRequiredService<IConfiguration>()));
builder.Services.AddHttpClient<RagServiceClient>((services, http) =>
{
    http.BaseAddress = services.GetRequiredService<RagSettings>().ServiceUrl;
    // Ask and readiness need different limits, so RagServiceClient applies them per call.
    http.Timeout = Timeout.InfiniteTimeSpan;
});

var app = builder.Build();

// Resolving once here makes an invalid RAG_* variable stop the process before it serves anything.
app.Services.GetRequiredService<RagSettings>();

app.Use(async (context, next) =>
{
    // TraceIdentifier is ASP.NET Core's own per-request ID; every handler, including the
    // exception handler below, reads the validated value from there.
    context.TraceIdentifier = RequestId.FromHeader(context.Request.Headers[RequestId.HeaderName]);
    // Added when the response starts, so it survives the exception handler clearing headers.
    context.Response.OnStarting(() =>
    {
        context.Response.Headers[RequestId.HeaderName] = context.TraceIdentifier;
        return Task.CompletedTask;
    });
    await next(context);
});

// Unexpected exceptions become the contract's internal_error. The middleware logs the exception;
// the client never sees its text. Requests aborted by the client are not reported as errors.
app.UseExceptionHandler(errorApp => errorApp.Run(context =>
    ApiError.InternalError.ToResult(context.TraceIdentifier).ExecuteAsync(context)));

app.MapGet("/health/live", () => Results.Ok(new { status = "live" }));
app.MapGet("/health/ready", (HttpContext context, RagServiceClient ragService) =>
    ragService.GetReadinessAsync(context.TraceIdentifier, context.RequestAborted));
app.MapPost("/api/ask", AskEndpoint.HandleAsync);

app.Run();
