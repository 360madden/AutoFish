local SessionState = {}

local function buildCounters()
    return {
        casts = 0,
        hooksets = 0,
        catches = 0,
        skillUps = 0,
        recoveries = 0,
        maintenanceActions = 0,
    }
end

function SessionState.create(config, activeProfile)
    return {
        mode = "idle",
        activeProfile = activeProfile or "starter-pond",
        lastAction = "bootstrap",
        lastReason = "lua controller initialized",
        remainingBait = config.baitCapacity,
        freeSlots = config.inventoryCapacity,
        counters = buildCounters(),
        alerts = {},
        bridgeOnline = false,
    }
end

function SessionState.resetMaintenanceResources(session, config)
    session.remainingBait = config.baitCapacity
    session.freeSlots = config.inventoryCapacity
end

return SessionState
