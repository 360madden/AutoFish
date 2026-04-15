using AutoFish.Contracts.Models;
using AutoFish.Contracts.Serialization;

namespace AutoFish.App.Profiles;

public sealed class JsonProfileCatalog : IProfileCatalog
{
    private readonly IReadOnlyList<FishingProfile> _profiles;
    private readonly Dictionary<string, FishingProfile> _profilesById;

    public JsonProfileCatalog(string profilesDirectory)
    {
        if (!Directory.Exists(profilesDirectory))
        {
            throw new DirectoryNotFoundException($"Profiles directory not found: {profilesDirectory}");
        }

        var loadedProfiles = Directory
            .EnumerateFiles(profilesDirectory, "*.json", SearchOption.TopDirectoryOnly)
            .OrderBy(Path.GetFileNameWithoutExtension, StringComparer.OrdinalIgnoreCase)
            .Select(path => new
            {
                Path = path,
                Profile = ContractJson.Deserialize<FishingProfile>(File.ReadAllText(path)),
            })
            .ToArray();

        if (loadedProfiles.Length == 0)
        {
            throw new InvalidOperationException($"No profile files were found in {profilesDirectory}");
        }

        var validationErrors = new List<string>();
        var profiles = new List<FishingProfile>(loadedProfiles.Length);
        var profilesById = new Dictionary<string, FishingProfile>(StringComparer.OrdinalIgnoreCase);
        var profilePathsById = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        foreach (var entry in loadedProfiles)
        {
            validationErrors.AddRange(ProfileValidation.Validate(entry.Profile, entry.Path));

            if (!string.IsNullOrWhiteSpace(entry.Profile.Id))
            {
                if (profilePathsById.TryGetValue(entry.Profile.Id, out var existingPath))
                {
                    validationErrors.Add($"{entry.Path}: duplicate profile id '{entry.Profile.Id}' already used by '{existingPath}'.");
                }
                else
                {
                    profilePathsById[entry.Profile.Id] = entry.Path;
                    profilesById[entry.Profile.Id] = entry.Profile;
                }
            }

            profiles.Add(entry.Profile);
        }

        if (validationErrors.Count > 0)
        {
            throw new InvalidDataException("Profile validation failed:" + Environment.NewLine + string.Join(Environment.NewLine, validationErrors));
        }

        _profiles = profiles;
        _profilesById = profilesById;
    }

    public IReadOnlyList<FishingProfile> GetAll() => _profiles;

    public FishingProfile GetById(string id)
    {
        if (_profilesById.TryGetValue(id, out var profile))
        {
            return profile;
        }

        throw new KeyNotFoundException($"Unknown profile id: {id}");
    }
}
