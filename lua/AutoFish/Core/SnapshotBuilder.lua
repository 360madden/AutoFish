local Observation = AutoFish.Core.Observation

local SnapshotBuilder = {}

local function normalizeCounters(session)
    local counters = type(session.counters) == "table" and session.counters or {}

    return {
        casts = type(counters.casts) == "number" and math.max(0, math.floor(counters.casts)) or 0,
        hooksets = type(counters.hooksets) == "number" and math.max(0, math.floor(counters.hooksets)) or 0,
        catches = type(counters.catches) == "number" and math.max(0, math.floor(counters.catches)) or 0,
        skillUps = type(counters.skillUps) == "number" and math.max(0, math.floor(counters.skillUps)) or 0,
        recoveries = type(counters.recoveries) == "number" and math.max(0, math.floor(counters.recoveries)) or 0,
        maintenanceActions = type(counters.maintenanceActions) == "number" and math.max(0, math.floor(counters.maintenanceActions)) or 0,
    }
end

local function normalizeAlerts(session)
    local sourceAlerts = type(session.alerts) == "table" and session.alerts or {}
    local alerts = {}

    for _, alert in ipairs(sourceAlerts) do
        if type(alert) == "string" and alert ~= "" then
            alerts[#alerts + 1] = alert
        end
    end

    return alerts
end

function SnapshotBuilder.build(session, characterName, observation)
    session = type(session) == "table" and session or {}
    observation = observation or {}
    local counters = normalizeCounters(session)
    local alerts = normalizeAlerts(session)

    return {
        characterName = characterName or "Unknown",
        activeProfile = type(session.activeProfile) == "string" and session.activeProfile or "starter-pond",
        mode = type(session.mode) == "string" and session.mode or "idle",
        inGame = Observation.boolean(observation, "inGame", true),
        nearWater = Observation.boolean(observation, "nearWater", true),
        inCombat = Observation.boolean(observation, "inCombat", false),
        inventoryFull = Observation.boolean(observation, "inventoryFull", false) or ((type(session.freeSlots) == "number" and session.freeSlots or 0) <= 0),
        bridgeOnline = session.bridgeOnline == true,
        remainingBait = type(session.remainingBait) == "number" and math.max(0, math.floor(session.remainingBait)) or 0,
        freeSlots = type(session.freeSlots) == "number" and math.max(0, math.floor(session.freeSlots)) or 0,
        lastAction = type(session.lastAction) == "string" and session.lastAction or "pause",
        lastReason = type(session.lastReason) == "string" and session.lastReason or "snapshot generated from incomplete session data",
        reticleColor = Observation.string(observation, "reticleColor", "unknown"),
        updatedAtUtc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
        counters = counters,
        alerts = alerts,
    }
end

AutoFish = AutoFish or {}
AutoFish.Core = AutoFish.Core or {}
AutoFish.Core.SnapshotBuilder = SnapshotBuilder
if require ~= nil then return SnapshotBuilder end
