using AutoFish.Contracts.Models;

namespace AutoFish.App.Services;

public interface ISessionService
{
    IReadOnlyList<FishingProfile> Profiles { get; }

    SessionStatus GetSnapshot();

    IReadOnlyList<string> GetBridgeLog();

    FishingProfile GetProfile(string id);

    void SendCommand(BridgeCommand command);
}
