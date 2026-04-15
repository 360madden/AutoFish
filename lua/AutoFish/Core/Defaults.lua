local Defaults = {}

local function normalizeInteger(value, fallback)
    if type(value) ~= "number" then
        return fallback
    end

    return math.max(0, math.floor(value))
end

local function normalizeBoolean(value, fallback)
    if type(value) == "boolean" then
        return value
    end

    return fallback
end

function Defaults.normalize(config)
    config = config or {}

    local reactionFloorMs = normalizeInteger(config.reactionFloorMs, 60)
    local reactionCeilingMs = normalizeInteger(config.reactionCeilingMs, 180)
    if reactionCeilingMs < reactionFloorMs then
        reactionCeilingMs = reactionFloorMs
    end

    return {
        baitCapacity = normalizeInteger(config.baitCapacity, 20),
        inventoryCapacity = normalizeInteger(config.inventoryCapacity, 12),
        reactionFloorMs = reactionFloorMs,
        reactionCeilingMs = reactionCeilingMs,
        biteTimeoutMs = normalizeInteger(config.biteTimeoutMs, 12000),
        lootTimeoutMs = normalizeInteger(config.lootTimeoutMs, 2200),
        rebaitAtOrBelow = normalizeInteger(config.rebaitAtOrBelow, 5),
        maintenanceAtFreeSlotsOrBelow = normalizeInteger(config.maintenanceAtFreeSlotsOrBelow, 2),
        maxRecoveryAttempts = normalizeInteger(config.maxRecoveryAttempts, 3),
        pauseOnCombat = normalizeBoolean(config.pauseOnCombat, true),
        pauseOnBridgeLoss = normalizeBoolean(config.pauseOnBridgeLoss, false),
        recoverOnDrift = normalizeBoolean(config.recoverOnDrift, true),
    }
end

return Defaults
