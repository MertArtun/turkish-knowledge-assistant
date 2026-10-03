using System.Text.Json;

namespace SupportAssistant.Api;

/// <summary>POST /api/ask: validates the external request, then relays it to the RAG service.</summary>
public static class AskEndpoint
{
    // Contract limits (docs/project-spec.md §5). Kestrel enforces the body limit (Program.cs).
    public const int MaxBodyBytes = 16 * 1024;
    public const int MaxQuestionCharacters = 2000;

    public static async Task<IResult> HandleAsync(HttpContext context, RagServiceClient ragService)
    {
        var requestId = context.TraceIdentifier;
        AskRequest? request;
        try
        {
            // The contract options reject unknown fields, unknown enum values, non-ISO dates and
            // missing or null required fields with a JsonException.
            request = await JsonSerializer.DeserializeAsync<AskRequest>(
                context.Request.Body, ContractJson.Options, context.RequestAborted);
        }
        catch (JsonException)
        {
            return ApiError.InvalidRequest.ToResult(requestId);
        }
        catch (BadHttpRequestException exception)
        {
            // Kestrel throws while the body is read, e.g. once it passes MaxBodyBytes.
            var error = exception.StatusCode == StatusCodes.Status413PayloadTooLarge
                ? ApiError.PayloadTooLarge
                : ApiError.InvalidRequest;
            return error.ToResult(requestId);
        }
        if (request is null)
        {
            // The body was the JSON literal null.
            return ApiError.InvalidRequest.ToResult(requestId);
        }

        var question = request.Question.Trim();
        if (!HasValidLength(question))
        {
            return ApiError.InvalidQuestion.ToResult(requestId);
        }
        return await ragService.AskAsync(request with { Question = question }, requestId, context.RequestAborted);
    }

    private static bool HasValidLength(string trimmedQuestion)
    {
        // Counted in Unicode code points like Python's len(), so both services agree on
        // "2000 characters"; string.Length would count an emoji as two.
        var characters = trimmedQuestion.EnumerateRunes().Count();
        return characters is > 0 and <= MaxQuestionCharacters;
    }
}
