using System.Net;
using System.Text.Json.Nodes;

namespace SupportAssistant.Api.Tests;

public class AskValidationTests
{
    private const string QuestionMessage = "Soru boş olamaz ve en fazla 2000 karakter olabilir.";

    public static TheoryData<string> InvalidBodies => new()
    {
        "",
        "not json",
        "null",
        "[]",
        """{}""",
        """{"question": null}""",
        """{"question": 5}""",
        // Unknown fields, including wrongly cased known ones, are rejected like Pydantic's extra="forbid".
        """{"question": "a", "extra": 1}""",
        """{"Question": "a"}""",
        // Only the exact snake_case enum names; the built-in converter would accept the next four.
        """{"question": "a", "mode": "fast"}""",
        """{"question": "a", "mode": "Generative"}""",
        """{"question": "a", "mode": "EVIDENCEONLY"}""",
        """{"question": "a", "mode": "generative, evidence_only"}""",
        """{"question": "a", "mode": 0}""",
        // as_of is a plain ISO date: no time part, no other format, no timestamp, no impossible day.
        """{"question": "a", "as_of": "2026-10-04T00:00:00"}""",
        """{"question": "a", "as_of": "04.10.2026"}""",
        """{"question": "a", "as_of": "2026-02-30"}""",
        """{"question": "a", "as_of": 1790035200}""",
        """{"question": "a", "as_of": ""}""",
        // A given scope needs all three fields and nothing else.
        """{"question": "a", "scope": {"country": "TR", "customer_type": "B2B"}}""",
        """{"question": "a", "scope": {"country": null, "customer_type": "B2B", "product": "MH-10"}}""",
        """{"question": "a", "scope": {"country": "TR", "customer_type": "B2B", "product": "MH-10", "region": "x"}}""",
        """{"question": "a", "scope": "TR"}""",
    };

    [Theory]
    [MemberData(nameof(InvalidBodies))]
    public async Task InvalidBody_Returns400InvalidRequest_WithoutCallingRagService(string body)
    {
        await using var api = new ApiUnderTest();

        var response = await api.AskAsync(body);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var error = await ReadErrorAsync(response);
        Assert.Equal("invalid_request", error["code"]!.GetValue<string>());
        Assert.Empty(api.Rag.Requests);
    }

    public static TheoryData<string> InvalidQuestions => new()
    {
        "",
        "   ",
        "\n\t ",
        new string('a', 2001),
        string.Concat(Enumerable.Repeat("😀", 2001)),
    };

    [Theory]
    [MemberData(nameof(InvalidQuestions))]
    public async Task EmptyOrTooLongQuestion_Returns400WithQuestionMessage(string question)
    {
        await using var api = new ApiUnderTest();

        var response = await api.AskAsync(new JsonObject { ["question"] = question }.ToJsonString());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var error = await ReadErrorAsync(response);
        Assert.Equal("invalid_request", error["code"]!.GetValue<string>());
        Assert.Equal(QuestionMessage, error["message"]!.GetValue<string>());
        Assert.Empty(api.Rag.Requests);
    }

    [Fact]
    public async Task Question_IsTrimmedBeforeTheLengthCheck_AndForwardedTrimmed()
    {
        await using var api = new ApiUnderTest();
        api.Rag.AnswersWithFixture("ask-response-answered.json");
        var question = new string('a', 2000);

        var response = await api.AskAsync(new JsonObject { ["question"] = $"  {question}\n" }.ToJsonString());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var sent = JsonNode.Parse(Assert.Single(api.Rag.Requests).Body!)!;
        Assert.Equal(question, sent["question"]!.GetValue<string>());
    }

    [Fact]
    public async Task QuestionLength_CountsCharactersLikePython_NotUtf16Units()
    {
        await using var api = new ApiUnderTest();
        api.Rag.AnswersWithFixture("ask-response-answered.json");
        // 2000 characters, 4000 UTF-16 units: Python's len() says 2000, so the API must accept it.
        var question = string.Concat(Enumerable.Repeat("😀", 2000));

        var response = await api.AskAsync(new JsonObject { ["question"] = question }.ToJsonString());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task InvalidRequest_StillCarriesTheRequestId()
    {
        await using var api = new ApiUnderTest();

        var response = await api.AskAsync("""{"question": ""}""", requestId: "client-42");

        var body = JsonNode.Parse(await response.Content.ReadAsStringAsync())!;
        Assert.Equal("client-42", body["request_id"]!.GetValue<string>());
        Assert.Equal("client-42", Assert.Single(response.Headers.GetValues("X-Request-ID")));
    }

    private static async Task<JsonNode> ReadErrorAsync(HttpResponseMessage response)
    {
        var body = JsonNode.Parse(await response.Content.ReadAsStringAsync())!.AsObject();
        Assert.Equal(["request_id", "error"], body.Select(property => property.Key));
        return body["error"]!;
    }
}
