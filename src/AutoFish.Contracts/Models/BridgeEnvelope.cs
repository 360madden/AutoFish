using System.Text.Json;

namespace AutoFish.Contracts.Models;

public sealed record BridgeEnvelope(
    BridgeMessageType MessageType,
    string ContractVersion,
    DateTimeOffset IssuedAtUtc,
    JsonElement Payload);
