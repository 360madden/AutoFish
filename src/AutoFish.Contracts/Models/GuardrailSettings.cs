namespace AutoFish.Contracts.Models;

public sealed record GuardrailSettings(
    bool PauseOnCombat,
    bool PauseOnBridgeLoss,
    bool RecoverOnDrift);
