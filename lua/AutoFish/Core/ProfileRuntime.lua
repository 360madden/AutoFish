local Defaults = AutoFish.Core.Defaults

local ProfileRuntime = {}

function ProfileRuntime.fromProfile(profile)
    if type(profile) ~= "table" then
        return Defaults.normalize({})
    end

    local thresholds = profile.thresholds or {}
    local guardrails = profile.guardrails or {}
    local pacing = profile.pacing or {}

    return Defaults.normalize({
        reactionFloorMs = pacing.reactionFloorMs,
        reactionCeilingMs = pacing.reactionCeilingMs,
        biteTimeoutMs = pacing.biteTimeoutMs,
        lootTimeoutMs = pacing.lootTimeoutMs,
        rebaitAtOrBelow = thresholds.rebaitAtOrBelow,
        maintenanceAtFreeSlotsOrBelow = thresholds.maintenanceAtFreeSlotsOrBelow,
        maxRecoveryAttempts = thresholds.maxRecoveryAttempts,
        pauseOnCombat = guardrails.pauseOnCombat,
        pauseOnBridgeLoss = guardrails.pauseOnBridgeLoss,
        recoverOnDrift = guardrails.recoverOnDrift,
    })
end

AutoFish = AutoFish or {}
AutoFish.Core = AutoFish.Core or {}
AutoFish.Core.ProfileRuntime = ProfileRuntime
if require ~= nil then return ProfileRuntime end
