local Observation = {}

local snakeCaseAliases = {
    characterName = "character_name",
    inGame = "in_game",
    nearWater = "near_water",
    inCombat = "in_combat",
    inventoryFull = "inventory_full",
    baitAvailable = "bait_available",
    lineCast = "line_cast",
    bobberVisible = "bobber_visible",
    biteDetected = "bite_detected",
    lootReady = "loot_window_open",
    skillUpReady = "skill_up_ready",
    durabilityLow = "durability_low",
    canCast = "can_cast",
    stuckForSeconds = "stuck_for_seconds",
    reticleColor = "reticle_color",
}

function Observation.get(observation, key, fallback)
    if type(observation) ~= "table" then
        return fallback
    end

    local value = observation[key]
    if value == nil then
        local alias = snakeCaseAliases[key]
        if alias ~= nil then
            value = observation[alias]
        end
    end

    if value == nil then
        return fallback
    end

    return value
end

function Observation.boolean(observation, key, fallback)
    local value = Observation.get(observation, key, fallback)
    if type(value) == "boolean" then
        return value
    end

    return fallback
end

function Observation.number(observation, key, fallback)
    local value = Observation.get(observation, key, fallback)
    if type(value) == "number" then
        return value
    end

    return fallback
end

function Observation.string(observation, key, fallback)
    local value = Observation.get(observation, key, fallback)
    if type(value) == "string" then
        return value
    end

    return fallback
end

AutoFish = AutoFish or {}
AutoFish.Core = AutoFish.Core or {}
AutoFish.Core.Observation = Observation
if require ~= nil then return Observation end
