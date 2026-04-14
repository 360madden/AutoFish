using System.Text.Json;
using System.Text.Json.Serialization;

namespace AutoFish.Contracts.Serialization;

public static class ContractJson
{
    public static JsonSerializerOptions Options { get; } = BuildOptions();

    public static string Serialize<T>(T value)
    {
        return JsonSerializer.Serialize(value, Options);
    }

    public static T Deserialize<T>(string json)
    {
        var result = JsonSerializer.Deserialize<T>(json, Options);
        if (result is null)
        {
            throw new InvalidOperationException($"Unable to deserialize {typeof(T).Name}.");
        }

        return result;
    }

    private static JsonSerializerOptions BuildOptions()
    {
        var options = new JsonSerializerOptions(JsonSerializerDefaults.Web)
        {
            WriteIndented = true,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        };

        options.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.SnakeCaseLower, allowIntegerValues: false));
        return options;
    }
}
