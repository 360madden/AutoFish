namespace AutoFish.Contracts.Models;

public sealed record SessionCounters(
    int Casts,
    int Hooksets,
    int Catches,
    int SkillUps,
    int Recoveries,
    int MaintenanceActions);
