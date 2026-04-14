namespace AutoFish.Contracts.Models;

public sealed record TimingSettings(
    int ReactionFloorMs,
    int ReactionCeilingMs,
    int BiteTimeoutMs,
    int LootTimeoutMs);
