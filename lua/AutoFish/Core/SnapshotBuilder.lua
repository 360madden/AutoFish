local SnapshotBuilder = {}

function SnapshotBuilder.build(session, characterName, observation)
    observation = observation or {}

    return {
        characterName = characterName or "Unknown",
        activeProfile = session.activeProfile,
        mode = session.mode,
        inGame = observation.inGame ~= false,
        nearWater = observation.nearWater ~= false,
        inCombat = observation.inCombat == true,
        inventoryFull = observation.inventoryFull == true or session.freeSlots <= 0,
        bridgeOnline = session.bridgeOnline == true,
        remainingBait = session.remainingBait,
        freeSlots = session.freeSlots,
        lastAction = session.lastAction,
        lastReason = session.lastReason,
        counters = session.counters,
        alerts = session.alerts,
    }
end

return SnapshotBuilder
