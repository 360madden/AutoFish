using System.Text.RegularExpressions;
using AutoFish.Contracts.Models;

namespace AutoFish.App.Profiles;

internal static partial class ProfileValidation
{
    public static IReadOnlyList<string> Validate(FishingProfile profile, string sourcePath)
    {
        ArgumentNullException.ThrowIfNull(profile);

        var errors = new List<string>();

        ValidateRequiredString(profile.Id, "id");
        ValidateRequiredString(profile.DisplayName, "displayName");
        ValidateRequiredString(profile.ZoneName, "zoneName");
        ValidateRequiredString(profile.TargetSkill, "targetSkill");

        if (!string.IsNullOrWhiteSpace(profile.Id) && !ProfileIdPattern().IsMatch(profile.Id))
        {
            errors.Add($"{sourcePath}: property 'id' must match ^[a-z0-9-]+$.");
        }

        ValidateStringList(profile.EnabledSkills, "enabledSkills", minimumCount: 1);
        ValidateStringList(profile.Notes, "notes", minimumCount: 0);

        if (profile.Pacing is null)
        {
            errors.Add($"{sourcePath}: property 'pacing' must be an object.");
        }
        else
        {
            ValidateNonNegative(profile.Pacing.ReactionFloorMs, "pacing.reactionFloorMs");
            ValidateNonNegative(profile.Pacing.ReactionCeilingMs, "pacing.reactionCeilingMs");
            ValidateNonNegative(profile.Pacing.BiteTimeoutMs, "pacing.biteTimeoutMs");
            ValidateNonNegative(profile.Pacing.LootTimeoutMs, "pacing.lootTimeoutMs");

            if (profile.Pacing.ReactionCeilingMs < profile.Pacing.ReactionFloorMs)
            {
                errors.Add($"{sourcePath}.pacing: reactionCeilingMs must be greater than or equal to reactionFloorMs.");
            }
        }

        if (profile.Thresholds is null)
        {
            errors.Add($"{sourcePath}: property 'thresholds' must be an object.");
        }
        else
        {
            ValidateNonNegative(profile.Thresholds.RebaitAtOrBelow, "thresholds.rebaitAtOrBelow");
            ValidateNonNegative(profile.Thresholds.MaintenanceAtFreeSlotsOrBelow, "thresholds.maintenanceAtFreeSlotsOrBelow");
            ValidateNonNegative(profile.Thresholds.MaxRecoveryAttempts, "thresholds.maxRecoveryAttempts");
        }

        if (profile.Guardrails is null)
        {
            errors.Add($"{sourcePath}: property 'guardrails' must be an object.");
        }

        return errors;

        void ValidateRequiredString(string? value, string propertyName)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                errors.Add($"{sourcePath}: property '{propertyName}' must be a non-empty string.");
            }
        }

        void ValidateNonNegative(int value, string propertyName)
        {
            if (value < 0)
            {
                errors.Add($"{sourcePath}: property '{propertyName}' must be greater than or equal to 0.");
            }
        }

        void ValidateStringList(IReadOnlyList<string>? values, string propertyName, int minimumCount)
        {
            if (values is null)
            {
                errors.Add($"{sourcePath}: property '{propertyName}' is required.");
                return;
            }

            if (values.Count < minimumCount)
            {
                errors.Add($"{sourcePath}: property '{propertyName}' must contain at least {minimumCount} item(s).");
                return;
            }

            foreach (var value in values)
            {
                if (string.IsNullOrWhiteSpace(value))
                {
                    errors.Add($"{sourcePath}: property '{propertyName}' must contain only non-empty strings.");
                    return;
                }
            }
        }
    }

    [GeneratedRegex("^[a-z0-9-]+$")]
    private static partial Regex ProfileIdPattern();
}
