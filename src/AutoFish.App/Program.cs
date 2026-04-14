using AutoFish.App.Infrastructure;
using AutoFish.App.Profiles;
using AutoFish.App.Settings;
using AutoFish.App.Services;

namespace AutoFish.App;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        ApplicationConfiguration.Initialize();
        var profileCatalog = new JsonProfileCatalog(RepositoryPaths.FindProfilesDirectory());
        var settingsStore = new JsonHelperSettingsStore(RepositoryPaths.GetHelperSettingsFilePath());
        var settings = settingsStore.Load();
        Application.Run(new MainForm(
            new MockSessionService(profileCatalog, settings.LastSelectedProfileId),
            settingsStore,
            settings));
    }
}
