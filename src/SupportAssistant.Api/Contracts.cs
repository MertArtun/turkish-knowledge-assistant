using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.Unicode;

namespace SupportAssistant.Api;

// External contract (docs/project-spec.md §5). Shapes only: what each status means is defined
// and enforced by the RAG service (app/contracts.py); tests/contracts/*.json pins both sides.

[JsonConverter(typeof(SnakeCaseEnumConverter<AnswerMode>))]
public enum AnswerMode { Generative, EvidenceOnly }

[JsonConverter(typeof(SnakeCaseEnumConverter<AnswerStatus>))]
public enum AnswerStatus { Answered, Partial, InsufficientEvidence, EvidenceOnly }

[JsonConverter(typeof(SnakeCaseEnumConverter<ReasonCode>))]
public enum ReasonCode { NotInDocuments, UnsupportedScope, AsOfRequired, NoValidVersion }

[JsonConverter(typeof(SnakeCaseEnumConverter<ExclusionReason>))]
public enum ExclusionReason { Expired, FutureEffective, NotApproved, ScopeMismatch }

[JsonConverter(typeof(SnakeCaseEnumConverter<ReadinessStatus>))]
public enum ReadinessStatus { Ready, NotReady }

public sealed record Scope(string Country, string CustomerType, string Product);

// Optional fields stay null here; the RAG service resolves the defaults (today, TR/B2B/MH-10, APP_MODE).
public sealed record AskRequest(string Question, DateOnly? AsOf = null, Scope? Scope = null, AnswerMode? Mode = null);

public sealed record Claim(string Text, IReadOnlyList<string> SourceChunkIds);

public sealed record SourceSection(
    string ChunkId,
    string DocId,
    string DocumentTitle,
    string Version,
    string SectionId,
    IReadOnlyList<string> HeadingPath,
    string Quote,
    DateOnly ValidFrom,
    DateOnly? ValidTo);

public sealed record DocumentVersion(string DocId, string Version, DateOnly ValidFrom, DateOnly? ValidTo);

public sealed record ExcludedVersion(
    string DocId, string Version, DateOnly ValidFrom, DateOnly? ValidTo, ExclusionReason Reason);

public sealed record VersionDecision(
    string ProcedureId, DocumentVersion? Selected, IReadOnlyList<ExcludedVersion> Excluded);

public sealed record AskResponse(
    string RequestId,
    AnswerStatus Status,
    AnswerMode Mode,
    DateOnly EffectiveAsOf,
    Scope EffectiveScope,
    string? Answer,
    IReadOnlyList<Claim> Claims,
    IReadOnlyList<SourceSection> Sources,
    IReadOnlyList<SourceSection> Evidence,
    IReadOnlyList<string> MissingTopics,
    ReasonCode? ReasonCode,
    IReadOnlyList<VersionDecision> VersionDecisions,
    IReadOnlyList<string> RetrievedChunkIds);

public sealed record ErrorDetail(string Code, string Message);

public sealed record ErrorResponse(string RequestId, ErrorDetail Error);

public sealed record ReadinessChecks(bool CorpusIndex, bool EmbeddingModel);

public sealed record RunMetadata(
    AnswerMode AppMode,
    bool GenerationConfigured,
    string LlmModel,
    string EmbeddingModel,
    string? EmbeddingRevision,
    string? CorpusFingerprint,
    string? PromptHash,
    int TopK,
    double? MinRetrievalScore);

public sealed record ReadinessResponse(ReadinessStatus Status, ReadinessChecks Checks, RunMetadata RunMetadata);

/// <summary>The one serializer configuration for the client, the RAG service and the fixtures.</summary>
public static class ContractJson
{
    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        // Like Pydantic's extra="forbid": drift between C#, Python and the fixtures fails loudly.
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        // Missing required fields and nulls in non-nullable ones throw instead of becoming defaults.
        RespectNullableAnnotations = true,
        RespectRequiredConstructorParameters = true,
        // Keeps Turkish letters readable in curl output and eval reports. HTML-sensitive
        // characters (< > & ' and similar) are still written as \uXXXX escapes.
        Encoder = JavaScriptEncoder.Create(UnicodeRanges.All),
    };
}

/// <summary>
/// Reads and writes an enum as its exact snake_case name ("evidence_only"). The built-in
/// JsonStringEnumConverter also reads "Generative", "EVIDENCEONLY" and flag lists such as
/// "generative, evidence_only"; the contract, like Python's Literal types, allows none of them.
/// </summary>
public sealed class SnakeCaseEnumConverter<TEnum> : JsonConverter<TEnum>
    where TEnum : struct, Enum
{
    private static readonly Dictionary<string, TEnum> ValuesByName = Enum.GetValues<TEnum>()
        .ToDictionary(value => JsonNamingPolicy.SnakeCaseLower.ConvertName(value.ToString()));

    private static readonly Dictionary<TEnum, string> NamesByValue = ValuesByName
        .ToDictionary(pair => pair.Value, pair => pair.Key);

    public override TEnum Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        if (reader.TokenType == JsonTokenType.String && ValuesByName.TryGetValue(reader.GetString()!, out var value))
        {
            return value;
        }
        throw new JsonException($"Not a known {typeof(TEnum).Name} value.");
    }

    public override void Write(Utf8JsonWriter writer, TEnum value, JsonSerializerOptions options) =>
        writer.WriteStringValue(NamesByValue[value]);
}
