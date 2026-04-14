using System.Text.Json;
using AutoFish.Contracts.Models;

namespace AutoFish.Contracts.Serialization;

public static class BridgeEnvelopeFactory
{
    public const string CurrentContractVersion = "1.0.0";

    public static BridgeEnvelope Create<TPayload>(BridgeMessageType messageType, TPayload payload)
    {
        return new BridgeEnvelope(
            messageType,
            CurrentContractVersion,
            DateTimeOffset.UtcNow,
            JsonSerializer.SerializeToElement(payload, ContractJson.Options));
    }
}
