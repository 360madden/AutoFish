namespace AutoFish.Contracts.Models;

public sealed record FishingProfile(
    string Id,
    string DisplayName,
    string ZoneName,
    string TargetSkill,
    IReadOnlyList<string> EnabledSkills,
    string? BaitName,
    IReadOnlyList<string> Notes,
    TimingSettings Pacing,
    ThresholdSettings Thresholds,
    GuardrailSettings Guardrails);
