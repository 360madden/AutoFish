namespace AutoFish.Contracts.Models;

public sealed record ThresholdSettings(
    int RebaitAtOrBelow,
    int MaintenanceAtFreeSlotsOrBelow,
    int MaxRecoveryAttempts);
