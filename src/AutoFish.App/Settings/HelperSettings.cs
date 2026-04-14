namespace AutoFish.App.Settings;

public sealed record HelperSettings(
    string? LastSelectedProfileId = null,
    int RefreshIntervalMs = 1000);
