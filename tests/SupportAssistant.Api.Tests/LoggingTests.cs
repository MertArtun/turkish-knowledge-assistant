using System.Net;
using System.Text.Json.Nodes;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Console;
using Microsoft.Extensions.Options;

namespace SupportAssistant.Api.Tests;

/// <summary>
/// What the API logs: every line of a request carries its request ID, so it joins the RAG
/// service's log, and no line carries the question, the answer or document text.
/// </summary>
public class LoggingTests
{
    // Can only reach the log by copying the question (or a RAG reply that repeats it).
    private const string Marker = "gizli-ayrinti-4711";

    private static readonly string Request =
        $$"""{"question": "İade kargosunu kim ödüyor? {{Marker}}", "as_of": "2026-10-04"}""";

    public static TheoryData<string> Outcomes =>
        ["answered", "rag_error", "reply_outside_contract", "rag_timeout", "rag_unreachable"];

    [Theory]
    [MemberData(nameof(Outcomes))]
    public async Task EveryLineOfARequest_NamesItsRequestId_AndNeverTheQuestionOrAnswer(string outcome)
    {
        await using var api = new ApiUnderTest(("RAG_TIMEOUT_SECONDS", "0.2"));
        switch (outcome)
        {
            case "answered":
                api.Rag.AnswersWithFixture("ask-response-answered.json");
                break;
            case "rag_error":
                api.Rag.RepliesWith(
                    HttpStatusCode.ServiceUnavailable,
                    $$$"""{"request_id": "client-log", "error": {"code": "provider_unavailable", "message": "{{{Marker}}}"}}""");
                break;
            case "reply_outside_contract":
                api.Rag.RepliesWith(HttpStatusCode.OK, $$"""{"request_id": "client-log", "answer": "{{Marker}}"}""");
                break;
            case "rag_timeout":
                api.Rag.Hangs(new TaskCompletionSource(), new TaskCompletionSource());
                break;
            case "rag_unreachable":
                api.Rag.Reply = (_, _) => throw new HttpRequestException("Connection refused (rag:8000)");
                break;
        }
        var startupLines = api.Logs.Entries.Count;

        await api.AskAsync(Request, requestId: "client-log");

        var lines = api.Logs.Entries.Skip(startupLines).ToList();
        Assert.NotEmpty(lines);
        Assert.All(lines, line => Assert.Equal("client-log", line.Values.GetValueOrDefault("RequestId")));
        var written = string.Join("\n", lines.Select(line => line.AllText));
        var answered = JsonNode.Parse(Fixture.Read("ask-response-answered.json"))!;
        Assert.DoesNotContain(Marker, written);
        Assert.DoesNotContain(answered["answer"]!.GetValue<string>(), written);
        Assert.DoesNotContain(answered["sources"]![0]!["quote"]!.GetValue<string>(), written);
    }

    [Fact]
    public async Task UnsafeRequestId_NeverReachesTheLogs()
    {
        await using var api = new ApiUnderTest();
        api.Rag.AnswersWithFixture("ask-response-evidence-only.json");

        var response = await api.AskAsync(Request, requestId: "forged\n{\"LogLevel\":\"Critical\"}");

        var generated = Assert.Single(response.Headers.GetValues("X-Request-ID"));
        var written = string.Join("\n", api.Logs.Entries.Select(entry => entry.AllText));
        Assert.DoesNotContain("forged", written);
        Assert.Contains(generated, written);
    }

    [Fact]
    public async Task ConsoleLog_IsWrittenAsJsonLines()
    {
        await using var api = new ApiUnderTest();

        var console = api.Services.GetRequiredService<IOptionsMonitor<ConsoleLoggerOptions>>().CurrentValue;

        Assert.Equal(ConsoleFormatterNames.Json, console.FormatterName);
    }
}
