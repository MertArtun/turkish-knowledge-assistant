using System.Diagnostics;
using System.Globalization;
using System.Net.Http.Json;
using System.Text.Json;

namespace SupportAssistant.Api;

/// <summary>Where the RAG service is and how long /api/ask waits for it. Names match .env.example.</summary>
public sealed record RagSettings(Uri ServiceUrl, TimeSpan Timeout)
{
    public const string ServiceUrlVariable = "RAG_SERVICE_URL";
    public const string TimeoutVariable = "RAG_TIMEOUT_SECONDS";
    private const double MaxTimeoutSeconds = 300;

    /// <summary>Reads and validates the settings; errors name the variable, never its value.</summary>
    public static RagSettings Load(IConfiguration configuration) =>
        new(ReadServiceUrl(configuration[ServiceUrlVariable]), ReadTimeout(configuration[TimeoutVariable]));

    // Blank means "not set", as in the RAG service, so `RAG_TIMEOUT_SECONDS=` keeps the default.
    private static Uri ReadServiceUrl(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            return new Uri("http://rag:8000");
        }
        if (Uri.TryCreate(text, UriKind.Absolute, out var url)
            && (url.Scheme == Uri.UriSchemeHttp || url.Scheme == Uri.UriSchemeHttps))
        {
            return url;
        }
        throw new InvalidOperationException($"{ServiceUrlVariable} must be an absolute http or https URL.");
    }

    private static TimeSpan ReadTimeout(string? text)
    {
        // The default must stay above the RAG service's LLM_TIMEOUT_SECONDS (25 s), so a slow
        // model is reported by the RAG service as generation_timeout rather than cut off here.
        if (string.IsNullOrWhiteSpace(text))
        {
            return TimeSpan.FromSeconds(45);
        }
        if (double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out var seconds)
            && seconds > 0
            && seconds <= MaxTimeoutSeconds)
        {
            return TimeSpan.FromSeconds(seconds);
        }
        throw new InvalidOperationException(
            $"{TimeoutVariable} must be a number of seconds greater than 0 and at most {MaxTimeoutSeconds}.");
    }
}

/// <summary>
/// Typed HttpClient for the Python RAG service. It sends the validated request and turns whatever
/// comes back, or fails to come back, into this API's contract. Replies are parsed into the
/// contract types and written again; the RAG service's raw body is never passed through.
/// </summary>
public sealed class RagServiceClient(HttpClient http, RagSettings settings, ILogger<RagServiceClient> logger)
{
    // Readiness is a cheap, constant reply; a RAG service this slow is reported as upstream_timeout.
    private static readonly TimeSpan ReadinessTimeout = TimeSpan.FromSeconds(3);

    public async Task<IResult> AskAsync(AskRequest request, string requestId, CancellationToken requestAborted)
    {
        using var message = new HttpRequestMessage(HttpMethod.Post, "/internal/ask")
        {
            Content = JsonContent.Create(request, options: ContractJson.Options),
        };
        var reply = await SendAsync(message, settings.Timeout, requestId, requestAborted);
        if (reply.TransportError is { } transportError)
        {
            return transportError.ToResult(requestId);
        }
        if (!reply.IsSuccessStatusCode)
        {
            return MapErrorReply(reply, requestId).ToResult(requestId);
        }

        var answer = Parse<AskResponse>(reply, requestId);
        if (answer is null)
        {
            return ApiError.UpstreamInvalidResponse.ToResult(requestId);
        }
        if (answer.RequestId != requestId)
        {
            // The ID is the only link between both services' logs; a different one means the
            // RAG service ignored the header.
            logger.LogWarning("RAG service answered with a different request_id (request_id={RequestId})", requestId);
            return ApiError.UpstreamInvalidResponse.ToResult(requestId);
        }
        return Results.Json(answer, ContractJson.Options);
    }

    public async Task<IResult> GetReadinessAsync(string requestId, CancellationToken requestAborted)
    {
        using var message = new HttpRequestMessage(HttpMethod.Get, "/health/ready");
        var reply = await SendAsync(message, ReadinessTimeout, requestId, requestAborted);
        if (reply.TransportError is { } transportError)
        {
            return transportError.ToResult(requestId);
        }

        // While the RAG service loads, its port is closed (upstream_unavailable above); once it
        // answers, the only valid reply is a success status with a "ready" body.
        var readiness = reply.IsSuccessStatusCode ? Parse<ReadinessResponse>(reply, requestId) : null;
        return readiness is null
            ? ApiError.UpstreamInvalidResponse.ToResult(requestId)
            : Results.Json(readiness, ContractJson.Options);
    }

    private async Task<UpstreamReply> SendAsync(
        HttpRequestMessage message, TimeSpan timeout, string requestId, CancellationToken requestAborted)
    {
        message.Headers.Add(RequestId.HeaderName, requestId);
        // One token ends the call when either the caller disconnects or our timeout elapses.
        using var callCancellation = CancellationTokenSource.CreateLinkedTokenSource(requestAborted);
        callCancellation.CancelAfter(timeout);
        var started = Stopwatch.GetTimestamp();
        try
        {
            using var response = await http.SendAsync(message, callCancellation.Token);
            var body = await response.Content.ReadAsByteArrayAsync(callCancellation.Token);
            logger.LogInformation(
                "RAG service {RagUrl} replied HTTP {UpstreamStatus} in {ElapsedMs:F0} ms (request_id={RequestId})",
                message.RequestUri, (int)response.StatusCode, Stopwatch.GetElapsedTime(started).TotalMilliseconds, requestId);
            return new UpstreamReply((int)response.StatusCode, body, TransportError: null);
        }
        catch (OperationCanceledException) when (!requestAborted.IsCancellationRequested)
        {
            // The caller is still connected, so the cancellation came from our timeout.
            logger.LogWarning(
                "RAG service {RagUrl} timed out after {TimeoutSeconds} s (request_id={RequestId})",
                message.RequestUri, timeout.TotalSeconds, requestId);
            return UpstreamReply.Failed(ApiError.UpstreamTimeout);
        }
        catch (HttpRequestException exception)
        {
            logger.LogWarning(exception, "RAG service {RagUrl} is unreachable (request_id={RequestId})", message.RequestUri, requestId);
            return UpstreamReply.Failed(ApiError.UpstreamUnavailable);
        }
        // A caller disconnect lets OperationCanceledException propagate: nobody is left to answer,
        // and ASP.NET Core records the request as aborted rather than failed.
    }

    private ApiError MapErrorReply(UpstreamReply reply, string requestId)
    {
        var body = Parse<ErrorResponse>(reply, requestId);
        var error = body is null ? ApiError.UpstreamInvalidResponse : ApiError.FromRagServiceCode(body.Error.Code);
        logger.LogWarning(
            "RAG service replied HTTP {UpstreamStatus}, returned as {ErrorCode} (request_id={RequestId})",
            reply.StatusCode, error.Code, requestId);
        return error;
    }

    private T? Parse<T>(UpstreamReply reply, string requestId)
        where T : class
    {
        try
        {
            return JsonSerializer.Deserialize<T>(reply.Body, ContractJson.Options);
        }
        catch (JsonException exception)
        {
            // Only the JSON path is logged: the body can contain the question or document text.
            logger.LogWarning(
                "RAG service reply (HTTP {UpstreamStatus}) is not a valid {Contract} at {JsonPath} (request_id={RequestId})",
                reply.StatusCode, typeof(T).Name, exception.Path, requestId);
            return null;
        }
    }

    /// <summary>Either what the RAG service sent, or the transport error to report instead.</summary>
    private sealed record UpstreamReply(int StatusCode, byte[] Body, ApiError? TransportError)
    {
        public bool IsSuccessStatusCode => StatusCode is >= 200 and <= 299;

        public static UpstreamReply Failed(ApiError error) => new(0, [], error);
    }
}
