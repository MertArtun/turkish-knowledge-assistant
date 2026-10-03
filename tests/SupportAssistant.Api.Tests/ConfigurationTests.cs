using Microsoft.Extensions.DependencyInjection;

namespace SupportAssistant.Api.Tests;

public class ConfigurationTests
{
    [Fact]
    public async Task Defaults_PointAtTheComposeServiceWithA45SecondTimeout()
    {
        await using var api = new ApiUnderTest();

        var settings = api.Services.GetRequiredService<RagSettings>();

        Assert.Equal(new Uri("http://rag:8000"), settings.ServiceUrl);
        Assert.Equal(TimeSpan.FromSeconds(45), settings.Timeout);
    }

    [Fact]
    public async Task BlankValues_MeanNotSet_LikeInTheRagService()
    {
        await using var api = new ApiUnderTest(("RAG_SERVICE_URL", ""), ("RAG_TIMEOUT_SECONDS", " "));

        var settings = api.Services.GetRequiredService<RagSettings>();

        Assert.Equal(new Uri("http://rag:8000"), settings.ServiceUrl);
        Assert.Equal(TimeSpan.FromSeconds(45), settings.Timeout);
    }

    [Fact]
    public async Task ConfiguredValues_AreUsed()
    {
        await using var api = new ApiUnderTest(
            ("RAG_SERVICE_URL", "http://127.0.0.1:8000"), ("RAG_TIMEOUT_SECONDS", "30.5"));

        var settings = api.Services.GetRequiredService<RagSettings>();

        Assert.Equal(new Uri("http://127.0.0.1:8000"), settings.ServiceUrl);
        Assert.Equal(TimeSpan.FromSeconds(30.5), settings.Timeout);
    }

    [Theory]
    [InlineData("RAG_TIMEOUT_SECONDS", "0.000")]
    [InlineData("RAG_TIMEOUT_SECONDS", "-5")]
    [InlineData("RAG_TIMEOUT_SECONDS", "301")]
    [InlineData("RAG_TIMEOUT_SECONDS", "NaN")]
    [InlineData("RAG_TIMEOUT_SECONDS", "45s")]
    [InlineData("RAG_SERVICE_URL", "rag:8000")]
    [InlineData("RAG_SERVICE_URL", "ftp://rag:8000")]
    [InlineData("RAG_SERVICE_URL", "not a url")]
    public void InvalidValue_StopsStartup_NamingTheVariableButNotTheValue(string variable, string value)
    {
        var exception = Assert.ThrowsAny<Exception>(() => new ApiUnderTest((variable, value)));

        var message = exception.GetBaseException().Message;
        Assert.Contains(variable, message);
        Assert.DoesNotContain(value, message);
    }

    [Fact]
    public void ConfigurationNames_MatchEnvExample()
    {
        var names = File.ReadAllLines(Path.Combine(AppContext.BaseDirectory, "env.example"))
            .Where(line => line.Contains('=') && !line.TrimStart().StartsWith('#'))
            .Select(line => line[..line.IndexOf('=')])
            .ToHashSet();

        Assert.Contains(RagSettings.ServiceUrlVariable, names);
        Assert.Contains(RagSettings.TimeoutVariable, names);
    }
}
