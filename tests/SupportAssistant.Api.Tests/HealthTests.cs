using System.Net;
using Microsoft.AspNetCore.Mvc.Testing;

namespace SupportAssistant.Api.Tests;

public class HealthTests(WebApplicationFactory<Program> factory)
    : IClassFixture<WebApplicationFactory<Program>>
{
    [Fact]
    public async Task Live_ReturnsOkWithSameBodyAsRagService()
    {
        var client = factory.CreateClient();

        var response = await client.GetAsync("/health/live");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("""{"status":"live"}""", await response.Content.ReadAsStringAsync());
    }
}
