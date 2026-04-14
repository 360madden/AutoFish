using AutoFish.Contracts.Models;

namespace AutoFish.App.Profiles;

public interface IProfileCatalog
{
    IReadOnlyList<FishingProfile> GetAll();

    FishingProfile GetById(string id);
}
