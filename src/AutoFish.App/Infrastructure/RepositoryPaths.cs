namespace AutoFish.App.Infrastructure;

public static class RepositoryPaths
{
    public static string GetHelperSettingsFilePath()
    {
        var appDataDirectory = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "AutoFish");

        return Path.Combine(appDataDirectory, "helper-settings.json");
    }

    public static string FindProfilesDirectory()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            var candidate = Path.Combine(current.FullName, "profiles");
            if (Directory.Exists(candidate)
                && Directory.EnumerateFiles(candidate, "*.json", SearchOption.TopDirectoryOnly).Any())
            {
                return candidate;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Unable to locate the repository profiles directory from the current app base path.");
    }
}
