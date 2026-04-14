namespace AutoFish.Contracts.Models;

public sealed record SessionStatus(
    string CharacterName,
    string ActiveProfile,
    ControllerMode Mode,
    bool InGame,
    bool NearWater,
    bool InCombat,
    bool InventoryFull,
    bool BridgeOnline,
    int RemainingBait,
    int FreeSlots,
    string LastAction,
    string LastReason,
    DateTimeOffset UpdatedAtUtc,
    SessionCounters Counters,
    IReadOnlyList<string> Alerts);
