using System.Text.Json;

namespace AutoFish.App.Settings;

public sealed class JsonHelperSettingsStore : IHelperSettingsStore
{
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = true,
    };

    private readonly string _settingsFilePath;

    public JsonHelperSettingsStore(string settingsFilePath)
    {
        _settingsFilePath = settingsFilePath;
    }

    public HelperSettings Load()
    {
        if (!File.Exists(_settingsFilePath))
        {
            return new HelperSettings();
        }

        try
        {
            var json = File.ReadAllText(_settingsFilePath);
            return JsonSerializer.Deserialize<HelperSettings>(json, SerializerOptions) ?? new HelperSettings();
        }
        catch
        {
            return new HelperSettings();
        }
    }

    public void Save(HelperSettings settings)
    {
        var directory = Path.GetDirectoryName(_settingsFilePath);
        if (!string.IsNullOrWhiteSpace(directory))
        {
            Directory.CreateDirectory(directory);
        }

        File.WriteAllText(_settingsFilePath, JsonSerializer.Serialize(settings, SerializerOptions));
    }
}
