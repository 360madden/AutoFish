namespace AutoFish.App.Settings;

public interface IHelperSettingsStore
{
    HelperSettings Load();

    void Save(HelperSettings settings);
}
