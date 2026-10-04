# External API. Build from the repository root: docker build -f src/SupportAssistant.Api/Dockerfile .
# Build with the SDK that global.json pins; run on the smaller ASP.NET runtime image.
FROM mcr.microsoft.com/dotnet/sdk:10.0.102-noble AS build
WORKDIR /source
COPY global.json ./
COPY src/SupportAssistant.Api/SupportAssistant.Api.csproj src/SupportAssistant.Api/
RUN dotnet restore src/SupportAssistant.Api/SupportAssistant.Api.csproj
COPY src/SupportAssistant.Api/ src/SupportAssistant.Api/
RUN dotnet publish src/SupportAssistant.Api/SupportAssistant.Api.csproj --no-restore -c Release -o /app

# Chiseled: no shell or package manager. ASP.NET listens on 8080 in this image.
FROM mcr.microsoft.com/dotnet/aspnet:10.0.12-noble-chiseled
WORKDIR /app
COPY --from=build /app ./
# The image's built-in unprivileged user.
USER $APP_UID
ENTRYPOINT ["dotnet", "SupportAssistant.Api.dll"]
