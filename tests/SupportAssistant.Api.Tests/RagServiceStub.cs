using System.Net;
using System.Text;
using System.Text.Json.Nodes;

namespace SupportAssistant.Api.Tests;

/// <summary>
/// Replaces the Python RAG service at the HttpClient boundary, so the API is tested without a
/// third service. Records what the API sent and answers with whatever the test configured.
/// </summary>
internal sealed class RagServiceStub : HttpMessageHandler
{
    private readonly List<SentRequest> requests = [];

    public IReadOnlyList<SentRequest> Requests => requests;

    /// <summary>The stub's answer. By default any call is a test failure (surfaces as HTTP 500).</summary>
    public Func<SentRequest, CancellationToken, Task<HttpResponseMessage>> Reply { get; set; } =
        (_, _) => throw new InvalidOperationException("The test did not expect a call to the RAG service.");

    public void RepliesWith(HttpStatusCode status, string body) =>
        Reply = (_, _) => Task.FromResult(Response(status, body));

    /// <summary>Answers with a shared fixture whose request_id echoes the X-Request-ID it received.</summary>
    public void AnswersWithFixture(string fixtureName, HttpStatusCode status = HttpStatusCode.OK) =>
        Reply = (sent, _) =>
        {
            var body = JsonNode.Parse(Fixture.Read(fixtureName))!;
            body["request_id"] = sent.RequestId;
            return Task.FromResult(Response(status, body.ToJsonString()));
        };

    /// <summary>Never answers; completes <paramref name="cancelled"/> when the API cancels the call.</summary>
    public void Hangs(TaskCompletionSource started, TaskCompletionSource cancelled) =>
        Reply = async (_, cancellationToken) =>
        {
            started.TrySetResult();
            try
            {
                await Task.Delay(Timeout.Infinite, cancellationToken);
            }
            catch (OperationCanceledException)
            {
                cancelled.TrySetResult();
                throw;
            }
            throw new InvalidOperationException("Unreachable: the delay is infinite.");
        };

    public static HttpResponseMessage Response(HttpStatusCode status, string body) =>
        new(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") };

    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var sent = new SentRequest(
            request.Method.Method,
            request.RequestUri!.AbsolutePath,
            request.Headers.TryGetValues("X-Request-ID", out var ids) ? string.Join(",", ids) : null,
            request.Content?.Headers.ContentType?.MediaType,
            request.Content is null ? null : await request.Content.ReadAsStringAsync(cancellationToken));
        requests.Add(sent);
        return await Reply(sent, cancellationToken);
    }
}

internal sealed record SentRequest(
    string Method, string Path, string? RequestId, string? ContentType, string? Body);

internal static class Fixture
{
    public static string Read(string name) =>
        File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "contracts", name));

    public static void AssertSameJson(string expected, string actual) =>
        Assert.True(
            JsonNode.DeepEquals(JsonNode.Parse(expected), JsonNode.Parse(actual)),
            $"JSON differs.\nExpected: {expected}\nActual:   {actual}");
}
