namespace SupportAssistant.Api;

/// <summary>
/// The closed set of errors this API returns (docs/project-spec.md §5, "Hata cevabı"). Messages
/// are fixed Turkish texts, so an exception text, upstream body, file path, key or the user's
/// question can never reach the client through an error.
/// </summary>
public sealed record ApiError(string Code, int StatusCode, string Message)
{
    public static readonly ApiError InvalidRequest = new(
        "invalid_request",
        StatusCodes.Status400BadRequest,
        "İstek geçersiz. Kabul edilen alanlar: question, as_of (YYYY-MM-DD), "
        + "scope (country, customer_type, product) ve mode (generative | evidence_only).");

    public static readonly ApiError InvalidQuestion = new(
        "invalid_request",
        StatusCodes.Status400BadRequest,
        "Soru boş olamaz ve en fazla 2000 karakter olabilir.");

    // The RAG service's invalid_request. This API has already checked the schema, so only the
    // limits it leaves to the RAG service remain: the embedding model's token limit for the
    // question and the scope field lengths.
    public static readonly ApiError RejectedByRagService = new(
        "invalid_request",
        StatusCodes.Status400BadRequest,
        "Soru veya kapsam asistan servisinin sınırlarını aşıyor: soru arama modelinin işleyebileceği "
        + "uzunluğu aşmamalı, scope alanlarının her biri en fazla 64 karakter olmalı.");

    public static readonly ApiError PayloadTooLarge = new(
        "payload_too_large",
        StatusCodes.Status413PayloadTooLarge,
        "İstek gövdesi 16 KiB sınırını aşıyor.");

    public static readonly ApiError GenerationNotConfigured = new(
        "generation_not_configured",
        StatusCodes.Status503ServiceUnavailable,
        "Üretken cevap modu bu ortamda yapılandırılmamış. mode alanını evidence_only olarak gönderebilirsiniz.");

    public static readonly ApiError ProviderUnavailable = new(
        "provider_unavailable",
        StatusCodes.Status503ServiceUnavailable,
        "Dil modeli sağlayıcısı isteği şu anda karşılayamıyor. Biraz sonra tekrar deneyin.");

    public static readonly ApiError GenerationTimeout = new(
        "generation_timeout",
        StatusCodes.Status504GatewayTimeout,
        "Dil modeli zamanında cevap vermedi.");

    public static readonly ApiError InvalidGenerationOutput = new(
        "invalid_generation_output",
        StatusCodes.Status502BadGateway,
        "Dil modelinin cevabı kaynak doğrulamasından geçmedi; güvenilir bir cevap üretilemedi.");

    public static readonly ApiError UpstreamUnavailable = new(
        "upstream_unavailable",
        StatusCodes.Status503ServiceUnavailable,
        "Asistan servisine ulaşılamıyor.");

    public static readonly ApiError UpstreamTimeout = new(
        "upstream_timeout",
        StatusCodes.Status504GatewayTimeout,
        "Asistan servisi zamanında cevap vermedi.");

    public static readonly ApiError UpstreamInvalidResponse = new(
        "upstream_invalid_response",
        StatusCodes.Status502BadGateway,
        "Asistan servisinden sözleşmeye uymayan bir cevap alındı.");

    public static readonly ApiError InternalError = new(
        "internal_error",
        StatusCodes.Status500InternalServerError,
        "Beklenmeyen bir hata oluştu.");

    /// <summary>
    /// Maps an error code from the RAG service to this API's error. Only codes the RAG service is
    /// documented to produce are accepted; anything else (including codes only this API emits)
    /// means the two services disagree on the contract.
    /// </summary>
    public static ApiError FromRagServiceCode(string code) => code switch
    {
        "invalid_request" => RejectedByRagService,
        "generation_not_configured" => GenerationNotConfigured,
        "provider_unavailable" => ProviderUnavailable,
        "generation_timeout" => GenerationTimeout,
        "invalid_generation_output" => InvalidGenerationOutput,
        "internal_error" => InternalError,
        _ => UpstreamInvalidResponse,
    };

    public IResult ToResult(string requestId) => Results.Json(
        new ErrorResponse(requestId, new ErrorDetail(Code, Message)), ContractJson.Options, statusCode: StatusCode);
}
