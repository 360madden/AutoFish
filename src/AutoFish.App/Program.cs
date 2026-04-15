using AutoFish.App.Infrastructure;
using AutoFish.App.Profiles;
using AutoFish.App.Settings;
using AutoFish.App.Services;

namespace AutoFish.App;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        var validateProfilesOnly = args.Any(arg => string.Equals(arg, "--validate-profiles", StringComparison.OrdinalIgnoreCase));

        try
        {
            ApplicationConfiguration.Initialize();
            var profileCatalog = new JsonProfileCatalog(RepositoryPaths.FindProfilesDirectory());
            var settingsStore = new JsonHelperSettingsStore(RepositoryPaths.GetHelperSettingsFilePath());
            var settings = settingsStore.Load();

            if (validateProfilesOnly)
            {
                Console.WriteLine($"Helper profile loading validated for {profileCatalog.GetAll().Count} profile(s).");
                return 0;
            }

            Application.Run(new MainForm(
                new MockSessionService(profileCatalog, settings.LastSelectedProfileId),
                settingsStore,
                settings));

            return 0;
        }
        catch (Exception ex)
        {
            if (!validateProfilesOnly)
            {
                MessageBox.Show(
                    ex.Message,
                    "AutoFish startup error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
            }

            Console.Error.WriteLine(ex.Message);
            return 1;
        }
    }
}
