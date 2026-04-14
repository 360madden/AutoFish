local ViewModel = {}

function ViewModel.fromSnapshot(snapshot, bridgeStatus)
    return {
        title = "AutoFish",
        mode = snapshot.mode,
        activeProfile = snapshot.activeProfile,
        remainingBait = tostring(snapshot.remainingBait),
        freeSlots = tostring(snapshot.freeSlots),
        bridgeState = bridgeStatus.bridgeOnline and "Online" or "Offline",
        lastAction = snapshot.lastAction,
        lastReason = snapshot.lastReason,
        casts = tostring(snapshot.counters.casts),
        hooksets = tostring(snapshot.counters.hooksets),
        catches = tostring(snapshot.counters.catches),
        skillUps = tostring(snapshot.counters.skillUps),
        recoveries = tostring(snapshot.counters.recoveries),
        maintenanceActions = tostring(snapshot.counters.maintenanceActions),
        alerts = snapshot.alerts,
        outboundQueued = tostring(bridgeStatus.outboundQueued),
        inboundQueued = tostring(bridgeStatus.inboundQueued),
    }
end

return ViewModel
