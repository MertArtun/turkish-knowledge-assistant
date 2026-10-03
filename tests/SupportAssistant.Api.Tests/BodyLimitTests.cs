using System.Net;
using System.Text;
using System.Text.Json.Nodes;

namespace SupportAssistant.Api.Tests;

/// <summary>The 16 KiB body limit is enforced by Kestrel, so these tests run on real Kestrel.</summary>
public class BodyLimitTests
{
    private const int LimitBytes = 16 * 1024;

    [Fact]
    public async Task BodyOverTheLimit_WithContentLength_Returns413PayloadTooLarge()
    {
        await using var api = ApiUnderTest.OnKestrel();

        var response = await api.Client.PostAsync("/api/ask", new ByteArrayContent(BodyOfSize(LimitBytes + 1)));

        await AssertPayloadTooLargeAsync(response);
        Assert.Empty(api.Rag.Requests);
    }

    [Fact]
    public async Task BodyOverTheLimit_SentChunked_Returns413PayloadTooLarge()
    {
        await using var api = ApiUnderTest.OnKestrel();
        // StreamContent over a non-seekable stream has no length, so HttpClient sends it chunked.
        var content = new StreamContent(new NonSeekableStream(BodyOfSize(LimitBytes + 1)));

        var response = await api.Client.PostAsync("/api/ask", content);

        Assert.Null(content.Headers.ContentLength);
        await AssertPayloadTooLargeAsync(response);
        Assert.Empty(api.Rag.Requests);
    }

    [Fact]
    public async Task BodyExactlyAtTheLimit_IsAccepted()
    {
        await using var api = ApiUnderTest.OnKestrel();
        api.Rag.AnswersWithFixture("ask-response-answered.json");

        var response = await api.Client.PostAsync("/api/ask", new ByteArrayContent(BodyOfSize(LimitBytes)));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Single(api.Rag.Requests);
    }

    /// <summary>A valid ask request padded with JSON whitespace to exactly <paramref name="size"/> bytes.</summary>
    private static byte[] BodyOfSize(int size)
    {
        var json = """{"question": "İade kargosunu kim ödüyor?"}""";
        var padding = size - Encoding.UTF8.GetByteCount(json);
        return Encoding.UTF8.GetBytes(json.Insert(1, new string(' ', padding)));
    }

    private static async Task AssertPayloadTooLargeAsync(HttpResponseMessage response)
    {
        Assert.Equal(HttpStatusCode.RequestEntityTooLarge, response.StatusCode);
        var body = JsonNode.Parse(await response.Content.ReadAsStringAsync())!;
        Assert.Equal("payload_too_large", body["error"]!["code"]!.GetValue<string>());
        Assert.Matches("^[0-9a-f]{32}$", body["request_id"]!.GetValue<string>());
    }

    private sealed class NonSeekableStream(byte[] bytes) : MemoryStream(bytes)
    {
        public override bool CanSeek => false;
    }
}
