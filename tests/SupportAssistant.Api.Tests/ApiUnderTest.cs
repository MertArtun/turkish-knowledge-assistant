using System.Text;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;

namespace SupportAssistant.Api.Tests;

/// <summary>The real API host (Program.cs) with only the RAG service's HTTP handler replaced.</summary>
internal sealed class ApiUnderTest : IAsyncDisposable
{
    private readonly WebApplicationFactory<Program> factory;

    public ApiUnderTest(params (string Key, string Value)[] settings)
        : this(useKestrel: false, settings)
    {
    }

    private ApiUnderTest(bool useKestrel, (string Key, string Value)[] settings)
    {
        factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            foreach (var (key, value) in settings)
            {
                builder.UseSetting(key, value);
            }
            builder.ConfigureTestServices(services => services
                .AddHttpClient<RagServiceClient>()
                .ConfigurePrimaryHttpMessageHandler(() => Rag));
        });
        if (useKestrel)
        {
            factory.UseKestrel(0);
        }
        Client = factory.CreateClient();
    }

    /// <summary>
    /// Runs on real Kestrel: the in-memory TestServer does not enforce request body limits.
    /// </summary>
    public static ApiUnderTest OnKestrel() => new(useKestrel: true, []);

    public RagServiceStub Rag { get; } = new();

    public HttpClient Client { get; }

    public IServiceProvider Services => factory.Services;

    public Task<HttpResponseMessage> AskAsync(
        string json, string? requestId = null, CancellationToken cancellationToken = default)
    {
        var request = new HttpRequestMessage(HttpMethod.Post, "/api/ask")
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json"),
        };
        if (requestId is not null)
        {
            request.Headers.TryAddWithoutValidation("X-Request-ID", requestId);
        }
        return Client.SendAsync(request, cancellationToken);
    }

    public async ValueTask DisposeAsync()
    {
        Client.Dispose();
        await factory.DisposeAsync();
    }
}
