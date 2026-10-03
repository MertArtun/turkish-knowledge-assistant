using System.Text.RegularExpressions;
using Microsoft.Extensions.Primitives;

namespace SupportAssistant.Api;

/// <summary>Correlation ID shared by the client, this API, the RAG service and both services' logs.</summary>
public static partial class RequestId
{
    public const string HeaderName = "X-Request-ID";

    // \z, not $: in .NET a $ also matches before a trailing "\n", which would let a line break
    // into log lines.
    [GeneratedRegex(@"^[A-Za-z0-9._-]{1,64}\z")]
    private static partial Regex SafePattern();

    /// <summary>Keeps the caller's ID only if it is one safe token; otherwise starts a new one.</summary>
    public static string FromHeader(StringValues values)
    {
        if (values.Count == 1 && values[0] is { } candidate && SafePattern().IsMatch(candidate))
        {
            return candidate;
        }
        return Guid.NewGuid().ToString("N");
    }
}
