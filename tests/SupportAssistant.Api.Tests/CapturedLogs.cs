using System.Collections.Concurrent;
using Microsoft.Extensions.Logging;

namespace SupportAssistant.Api.Tests;

/// <summary>
/// A logging provider that keeps what the API logs, after the app's own level filters, so tests
/// can check what would reach the console.
/// </summary>
internal sealed class CapturedLogs : ILoggerProvider
{
    private readonly ConcurrentQueue<LogEntry> entries = new();

    public IReadOnlyCollection<LogEntry> Entries => entries;

    public ILogger CreateLogger(string categoryName) => new Logger(categoryName, entries);

    public void Dispose()
    {
    }

    private sealed class Logger(string category, ConcurrentQueue<LogEntry> entries) : ILogger
    {
        public IDisposable? BeginScope<TState>(TState state)
            where TState : notnull => null;

        public bool IsEnabled(LogLevel logLevel) => true;

        public void Log<TState>(
            LogLevel logLevel, EventId eventId, TState state, Exception? exception, Func<TState, Exception?, string> formatter)
        {
            var values = state as IEnumerable<KeyValuePair<string, object?>> ?? [];
            entries.Enqueue(new LogEntry(
                category,
                formatter(state, exception),
                values.ToDictionary(pair => pair.Key, pair => pair.Value?.ToString()),
                exception?.ToString()));
        }
    }
}

/// <summary>One log entry: everything a sink could write (message, structured values, exception).</summary>
internal sealed record LogEntry(
    string Category, string Message, IReadOnlyDictionary<string, string?> Values, string? Exception)
{
    public string AllText =>
        $"{Category} {Message} {string.Join(" ", Values.Select(value => $"{value.Key}={value.Value}"))} {Exception}";
}
