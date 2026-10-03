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
        var ready = ReadyBody();
        api.Rag.RepliesWith(HttpStatusCode.OK, ready);

        var response = await api.Client.GetAsync("/health/ready");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Fixture.AssertSameJson(ready, await response.Content.ReadAsStringAsync());
        // Readiness never reaches /internal/ask, so it can never trigger an LLM call.
        var sent = Assert.Single(api.Rag.Requests);
        Assert.Equal(("GET", "/health/ready"), (sent.Method, sent.Path));
    }

    [Fact]
    public async Task NotReadyRagService_Returns503WithTheSameBodyShape()
    {
        await using var api = new ApiUnderTest();
        var notReady = Fixture.Read("readiness-not-ready.json");
        api.Rag.RepliesWith(HttpStatusCode.ServiceUnavailable, notReady);

        var response = await api.Client.GetAsync("/health/ready");

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Fixture.AssertSameJson(notReady, await response.Content.ReadAsStringAsync());
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

    [Theory]
    [InlineData(200, "{}")]
    [InlineData(500, "<html>Internal Server Error</html>")]
    [InlineData(200, """{"status": "ready", "checks": {"corpus_index": true, "embedding_model": true}}""")]
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

    private static string ReadyBody()
    {
        var body = JsonNode.Parse(Fixture.Read("readiness-not-ready.json"))!;
        body["status"] = "ready";
        body["checks"] = new JsonObject { ["corpus_index"] = true, ["embedding_model"] = true };
        body["run_metadata"]!["embedding_revision"] = "test-revision";
        body["run_metadata"]!["corpus_fingerprint"] = "test-fingerprint";
        body["run_metadata"]!["prompt_hash"] = "test-prompt-hash";
        body["run_metadata"]!["min_retrieval_score"] = 0.5;
        return body.ToJsonString();
    }

    private static async Task<string> ReadErrorCodeAsync(HttpResponseMessage response) =>
        JsonNode.Parse(await response.Content.ReadAsStringAsync())!["error"]!["code"]!.GetValue<string>();
}
