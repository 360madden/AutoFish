namespace AutoFish.Contracts.Models;

public sealed record BridgeCommand(
    BridgeCommandType CommandType,
    DateTimeOffset IssuedAtUtc,
    string? ProfileId = null,
    string? Notes = null,
    IReadOnlyDictionary<string, string>? Parameters = null);
