using System.Diagnostics;
using System.Net;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace SupportAssistant.Api.Tests;

public class AskRelayTests
{
    private static readonly Regex GeneratedId = new("^[0-9a-f]{32}$");

    [Fact]
    public async Task ValidRequest_IsSentToInternalAsk_AsSnakeCaseJson_WithTheRequestIdHeader()
    {
        await using var api = new ApiUnderTest();
        api.Rag.AnswersWithFixture("ask-response-answered.json");

        await api.AskAsync(Fixture.Read("ask-request.json"), requestId: "eval-E04.run_1");

        var sent = Assert.Single(api.Rag.Requests);
        Assert.Equal("POST", sent.Method);
        Assert.Equal("/internal/ask", sent.Path);
        Assert.Equal("application/json", sent.ContentType);
        Assert.Equal("eval-E04.run_1", sent.RequestId);
        Fixture.AssertSameJson(Fixture.Read("ask-request.json"), sent.Body!);
    }

    [Fact]
    public async Task OmittedOptionalFields_AreSentAsNull_SoTheRagServiceAppliesItsDefaults()
    {
        await using var api = new ApiUnderTest();
        api.Rag.AnswersWithFixture("ask-response-answered.json");

        await api.AskAsync("""{"question": "  İade kargosunu kim ödüyor?  "}""");

        Fixture.AssertSameJson(
            """{"question": "İade kargosunu kim ödüyor?", "as_of": null, "scope": null, "mode": null}""",
            Assert.Single(api.Rag.Requests).Body!);
    }

    [Theory]
    [InlineData("ask-response-answered.json")]
    [InlineData("ask-response-partial.json")]
    [InlineData("ask-response-insufficient-evidence.json")]
    [InlineData("ask-response-evidence-only.json")]
    public async Task SuccessfulAnswer_IsReturnedWithExactlyTheContractJson(string fixtureName)
    {
        await using var api = new ApiUnderTest();
        api.Rag.AnswersWithFixture(fixtureName);
        var expected = Fixture.Read(fixtureName);
        var fixtureRequestId = JsonNode.Parse(expected)!["request_id"]!.GetValue<string>();

        var response = await api.AskAsync(Fixture.Read("ask-request.json"), requestId: fixtureRequestId);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("application/json", response.Content.Headers.ContentType?.MediaType);
        Fixture.AssertSameJson(expected, await response.Content.ReadAsStringAsync());
    }

    [Fact]
    public async Task SafeIncomingRequestId_IsReturnedInHeaderAndBody()
    {
        await using var api = new ApiUnderTest();
        api.Rag.AnswersWithFixture("ask-response-answered.json");

        var response = await api.AskAsync("""{"question": "Soru"}""", requestId: "eval-E01.run_2");

        Assert.Equal("eval-E01.run_2", Assert.Single(response.Headers.GetValues("X-Request-ID")));
        var body = JsonNode.Parse(await response.Content.ReadAsStringAsync())!;
        Assert.Equal("eval-E01.run_2", body["request_id"]!.GetValue<string>());
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("has space")]
    [InlineData("semi;colon")]
    [InlineData("türkçe-ıd")]
    [InlineData("trailing-newline\n")] // a plain $ in the pattern would accept this
    [InlineData("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")] // 65 characters
    public async Task MissingOrUnsafeRequestId_IsReplacedByAGeneratedOne_UsedEverywhere(string? incoming)
    {
        await using var api = new ApiUnderTest();
        api.Rag.AnswersWithFixture("ask-response-answered.json");

        var response = await api.AskAsync("""{"question": "Soru"}""", requestId: incoming);

        var returned = Assert.Single(response.Headers.GetValues("X-Request-ID"));
        Assert.Matches(GeneratedId, returned);
        Assert.Equal(returned, Assert.Single(api.Rag.Requests).RequestId);
        var body = JsonNode.Parse(await response.Content.ReadAsStringAsync())!;
        Assert.Equal(returned, body["request_id"]!.GetValue<string>());
    }

    // Python HTTP status is what the RAG service would send; the API decides its own from the code.
    [Theory]
    [InlineData(400, "invalid_request", HttpStatusCode.BadRequest)]
    [InlineData(503, "service_not_ready", HttpStatusCode.ServiceUnavailable)]
    [InlineData(503, "generation_not_configured", HttpStatusCode.ServiceUnavailable)]
    [InlineData(503, "provider_unavailable", HttpStatusCode.ServiceUnavailable)]
    [InlineData(504, "generation_timeout", HttpStatusCode.GatewayTimeout)]
    [InlineData(502, "invalid_generation_output", HttpStatusCode.BadGateway)]
    [InlineData(500, "internal_error", HttpStatusCode.InternalServerError)]
    public async Task RagServiceError_IsMappedToItsCode_WithTheApisOwnSafeMessage(
        int ragStatus, string code, HttpStatusCode expectedStatus)
    {
        await using var api = new ApiUnderTest();
        const string leakyMessage = "Traceback: /app/secret_settings.py sk-test İade kargosunu";
        api.Rag.RepliesWith(
            (HttpStatusCode)ragStatus,
            $$$"""{"request_id": "rag-side-id", "error": {"code": "{{{code}}}", "message": "{{{leakyMessage}}}"}}""");

        var response = await api.AskAsync(Fixture.Read("ask-request.json"), requestId: "client-1");

        Assert.Equal(expectedStatus, response.StatusCode);
        var text = await response.Content.ReadAsStringAsync();
        var body = JsonNode.Parse(text)!;
        Assert.Equal("client-1", body["request_id"]!.GetValue<string>());
        Assert.Equal(code, body["error"]!["code"]!.GetValue<string>());
        Assert.False(string.IsNullOrWhiteSpace(body["error"]!["message"]!.GetValue<string>()));
        Assert.DoesNotContain("Traceback", text);
        Assert.DoesNotContain("sk-", text);
        Assert.DoesNotContain("İade kargosunu", text);
    }

    [Fact]
    public async Task RagServiceInvalidRequest_ExplainsTheLimitsOnlyTheRagServiceChecks()
    {
        // This API already checked the schema, so the RAG service's invalid_request can only mean
        // a question over the embedding model's token limit or a scope field over 64 characters.
        await using var api = new ApiUnderTest();
        api.Rag.RepliesWith(
            HttpStatusCode.BadRequest,
            """{"request_id": "client-1", "error": {"code": "invalid_request", "message": "x"}}""");

        var response = await api.AskAsync(Fixture.Read("ask-request.json"), requestId: "client-1");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var error = JsonNode.Parse(await response.Content.ReadAsStringAsync())!["error"]!;
        Assert.Equal("invalid_request", error["code"]!.GetValue<string>());
        Assert.Equal(ApiError.RejectedByRagService.Message, error["message"]!.GetValue<string>());
        Assert.NotEqual(ApiError.InvalidRequest.Message, ApiError.RejectedByRagService.Message);
    }

    public static TheoryData<int, string> InvalidRagReplies => new()
    {
        { 200, "not json" },
        { 200, "" },
        { 200, "null" },
        { 200, """{}""" },
        { 200, SuccessFixtureWith(body => body["status"] = "maybe") },
        { 200, SuccessFixtureWith(body => body["status"] = "Answered") },
        { 200, SuccessFixtureWith(body => body["diagnostics"] = new JsonObject()) },
        { 200, SuccessFixtureWith(body => body.Remove("retrieved_chunk_ids")) },
        { 200, SuccessFixtureWith(body => body["claims"] = null) },
        { 200, SuccessFixtureWith(body => body["effective_as_of"] = "2026-10-04T00:00:00") },
        // The ID links both services' logs; a different one means the header was ignored.
        { 200, SuccessFixtureWith(body => body["request_id"] = "some-other-id") },
        { 500, "<html>Internal Server Error</html>" },
        { 422, """{"detail": [{"loc": ["body", "question"], "msg": "Field required"}]}""" },
        // A code the RAG service never produces (only the API does) is contract drift, not a 413.
        { 413, """{"request_id": "client-1", "error": {"code": "payload_too_large", "message": "x"}}""" },
        { 503, """{"request_id": "client-1", "error": {"code": "something_new", "message": "x"}}""" },
    };

    [Theory]
    [MemberData(nameof(InvalidRagReplies))]
    public async Task ReplyOutsideTheContract_Returns502UpstreamInvalidResponse(int ragStatus, string ragBody)
    {
        await using var api = new ApiUnderTest();
        api.Rag.RepliesWith((HttpStatusCode)ragStatus, ragBody);

        var response = await api.AskAsync(Fixture.Read("ask-request.json"), requestId: "client-1");

        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        var body = JsonNode.Parse(await response.Content.ReadAsStringAsync())!;
        Assert.Equal("upstream_invalid_response", body["error"]!["code"]!.GetValue<string>());
        Assert.Equal("client-1", body["request_id"]!.GetValue<string>());
    }

    [Fact]
    public async Task UnreachableRagService_Returns503UpstreamUnavailable()
    {
        await using var api = new ApiUnderTest();
        api.Rag.Reply = (_, _) => throw new HttpRequestException("Connection refused (rag:8000)");

        var response = await api.AskAsync(Fixture.Read("ask-request.json"));

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        var text = await response.Content.ReadAsStringAsync();
        Assert.Equal("upstream_unavailable", JsonNode.Parse(text)!["error"]!["code"]!.GetValue<string>());
        Assert.DoesNotContain("rag:8000", text);
    }

    [Fact]
    public async Task SlowRagService_Returns504UpstreamTimeout_AndCancelsTheUpstreamCall()
    {
        await using var api = new ApiUnderTest(("RAG_TIMEOUT_SECONDS", "0.2"));
        var started = new TaskCompletionSource();
        var cancelled = new TaskCompletionSource();
        api.Rag.Hangs(started, cancelled);
        var stopwatch = Stopwatch.StartNew();

        var response = await api.AskAsync(Fixture.Read("ask-request.json"));

        Assert.Equal(HttpStatusCode.GatewayTimeout, response.StatusCode);
        Assert.True(stopwatch.Elapsed < TimeSpan.FromSeconds(10), $"took {stopwatch.Elapsed}");
        var body = JsonNode.Parse(await response.Content.ReadAsStringAsync())!;
        Assert.Equal("upstream_timeout", body["error"]!["code"]!.GetValue<string>());
        Assert.True(cancelled.Task.IsCompleted, "the upstream call must not keep running");
    }

    [Fact]
    public async Task ClientDisconnect_CancelsTheUpstreamCall()
    {
        await using var api = new ApiUnderTest(("RAG_TIMEOUT_SECONDS", "60"));
        var started = new TaskCompletionSource();
        var cancelled = new TaskCompletionSource();
        api.Rag.Hangs(started, cancelled);
        using var client = new CancellationTokenSource();

        var call = api.AskAsync(Fixture.Read("ask-request.json"), cancellationToken: client.Token);
        await started.Task.WaitAsync(TimeSpan.FromSeconds(10));
        await client.CancelAsync();

        // The upstream timeout is 60 s, so only the client's cancellation can end the call this fast.
        // (TestServer completes the client call only after the server side finishes, so this wait
        // must come first and be bounded.)
        await cancelled.Task.WaitAsync(TimeSpan.FromSeconds(10));
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => call);
    }

    [Fact]
    public async Task UnexpectedException_Returns500InternalError_WithoutExceptionText()
    {
        await using var api = new ApiUnderTest();
        api.Rag.Reply = (_, _) => throw new InvalidOperationException("boom at /srv/app/secret.cs");

        var response = await api.AskAsync(Fixture.Read("ask-request.json"), requestId: "client-9");

        Assert.Equal(HttpStatusCode.InternalServerError, response.StatusCode);
        var text = await response.Content.ReadAsStringAsync();
        var body = JsonNode.Parse(text)!;
        Assert.Equal("internal_error", body["error"]!["code"]!.GetValue<string>());
        Assert.Equal("client-9", body["request_id"]!.GetValue<string>());
        Assert.Equal("client-9", Assert.Single(response.Headers.GetValues("X-Request-ID")));
        Assert.DoesNotContain("boom", text);
        Assert.DoesNotContain("secret", text);
    }

    private static string SuccessFixtureWith(Action<JsonObject> change)
    {
        var body = JsonNode.Parse(Fixture.Read("ask-response-answered.json"))!.AsObject();
        body["request_id"] = "client-1";
        change(body);
        return body.ToJsonString();
    }
}
