using System.Diagnostics;
using System.Net;
using System.Text.Json.Nodes;

namespace SupportAssistant.Api.Tests;

public class ReadinessTests
{
    [Fact]
    public async Task ReadyRagService_Returns200WithTheTypedReadinessBody_UsingOnlyTheReadinessCall()
    {
        await using var api = new ApiUnderTest();
        var ready = Fixture.Read("readiness-ready.json");
        api.Rag.RepliesWith(HttpStatusCode.OK, ready);

        var response = await api.Client.GetAsync("/health/ready");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Fixture.AssertSameJson(ready, await response.Content.ReadAsStringAsync());
        // Readiness never reaches /internal/ask, so it can never trigger an LLM call.
        var sent = Assert.Single(api.Rag.Requests);
        Assert.Equal(("GET", "/health/ready"), (sent.Method, sent.Path));
    }

    [Fact]
    public async Task UnreachableRagService_Returns503UpstreamUnavailable()
    {
        await using var api = new ApiUnderTest();
        api.Rag.Reply = (_, _) => throw new HttpRequestException("Connection refused");

        var response = await api.Client.GetAsync("/health/ready");

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal("upstream_unavailable", await ReadErrorCodeAsync(response));
    }

    public static TheoryData<int, string> InvalidReadinessReplies => new()
    {
        { 200, "{}" },
        { 500, "<html>Internal Server Error</html>" },
        { 200, """{"status": "ready"}""" },
        // The RAG service loads everything before it listens, so it has no "not ready" body.
        { 503, ReadinessWith(body => body["status"] = "not_ready") },
        { 200, ReadinessWith(body => body["run_metadata"]!["corpus_fingerprint"] = null) },
        // A failure status contradicts a "ready" body; the API must not turn it into a 200.
        { 503, Fixture.Read("readiness-ready.json") },
    };

    [Theory]
    [MemberData(nameof(InvalidReadinessReplies))]
    public async Task ReplyOutsideTheContract_Returns502UpstreamInvalidResponse(int ragStatus, string ragBody)
    {
        await using var api = new ApiUnderTest();
        api.Rag.RepliesWith((HttpStatusCode)ragStatus, ragBody);

        var response = await api.Client.GetAsync("/health/ready");

        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Equal("upstream_invalid_response", await ReadErrorCodeAsync(response));
    }

    [Fact]
    public async Task SlowRagService_Returns504QuicklyEvenWithALongAskTimeout()
    {
        await using var api = new ApiUnderTest(("RAG_TIMEOUT_SECONDS", "60"));
        api.Rag.Hangs(new TaskCompletionSource(), new TaskCompletionSource());
        var stopwatch = Stopwatch.StartNew();

        var response = await api.Client.GetAsync("/health/ready");

        Assert.Equal(HttpStatusCode.GatewayTimeout, response.StatusCode);
        Assert.Equal("upstream_timeout", await ReadErrorCodeAsync(response));
        Assert.True(stopwatch.Elapsed < TimeSpan.FromSeconds(10), $"took {stopwatch.Elapsed}");
    }

    private static string ReadinessWith(Action<JsonNode> change)
    {
        var body = JsonNode.Parse(Fixture.Read("readiness-ready.json"))!;
        change(body);
        return body.ToJsonString();
    }

    private static async Task<string> ReadErrorCodeAsync(HttpResponseMessage response) =>
        JsonNode.Parse(await response.Content.ReadAsStringAsync())!["error"]!["code"]!.GetValue<string>();
}
