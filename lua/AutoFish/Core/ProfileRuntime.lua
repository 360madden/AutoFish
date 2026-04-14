local Defaults = require("AutoFish.Core.Defaults")

local ProfileRuntime = {}

function ProfileRuntime.fromProfile(profile)
    if type(profile) ~= "table" then
        return Defaults.normalize({})
    end

    local thresholds = profile.thresholds or {}
    local guardrails = profile.guardrails or {}

    return Defaults.normalize({
        rebaitAtOrBelow = thresholds.rebaitAtOrBelow,
        maintenanceAtFreeSlotsOrBelow = thresholds.maintenanceAtFreeSlotsOrBelow,
        pauseOnCombat = guardrails.pauseOnCombat,
        recoverOnDrift = guardrails.recoverOnDrift,
    })
end

return ProfileRuntime
