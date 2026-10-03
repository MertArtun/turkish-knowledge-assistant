using System.Text.Json;

namespace SupportAssistant.Api.Tests;

/// <summary>
/// The C# side of the shared fixtures: every file must read into the C# contract types and write
/// back to the same JSON (names, enum spellings, nulls, dates). Python runs the same check.
/// </summary>
public class ContractFixtureTests
{
    public static TheoryData<string, Type> Fixtures => new()
    {
        { "ask-request.json", typeof(AskRequest) },
        { "ask-response-answered.json", typeof(AskResponse) },
        { "ask-response-partial.json", typeof(AskResponse) },
        { "ask-response-insufficient-evidence.json", typeof(AskResponse) },
        { "ask-response-evidence-only.json", typeof(AskResponse) },
        { "error-response.json", typeof(ErrorResponse) },
        { "readiness-not-ready.json", typeof(ReadinessResponse) },
    };

    [Theory]
    [MemberData(nameof(Fixtures))]
    public void Fixture_RoundTripsThroughTheCSharpContract(string fixtureName, Type contractType)
    {
        var json = Fixture.Read(fixtureName);

        var value = JsonSerializer.Deserialize(json, contractType, ContractJson.Options);
        var written = JsonSerializer.Serialize(value, contractType, ContractJson.Options);

        Fixture.AssertSameJson(json, written);
    }

    [Fact]
    public void EveryFixtureFile_IsCoveredByTheRoundTripTest()
    {
        var files = Directory.GetFiles(Path.Combine(AppContext.BaseDirectory, "contracts"), "*.json")
            .Select(Path.GetFileName)
            .Order();

        Assert.Equal(Fixtures.Select(row => (string)row[0]).Order(), files);
    }

    [Fact]
    public void ErrorFixtureMessage_IsTheApisOwnQuestionMessage()
    {
        var fixture = JsonSerializer.Deserialize<ErrorResponse>(
            Fixture.Read("error-response.json"), ContractJson.Options)!;

        Assert.Equal(ApiError.InvalidQuestion.Code, fixture.Error.Code);
        Assert.Equal(ApiError.InvalidQuestion.Message, fixture.Error.Message);
    }
}
