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

        _profiles = Directory
            .EnumerateFiles(profilesDirectory, "*.json", SearchOption.TopDirectoryOnly)
            .OrderBy(Path.GetFileNameWithoutExtension, StringComparer.OrdinalIgnoreCase)
            .Select(path => ContractJson.Deserialize<FishingProfile>(File.ReadAllText(path)))
            .ToArray();

        if (_profiles.Count == 0)
        {
            throw new InvalidOperationException($"No profile files were found in {profilesDirectory}");
        }

        _profilesById = _profiles.ToDictionary(profile => profile.Id, StringComparer.OrdinalIgnoreCase);
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
