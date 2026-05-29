local ViewModel = {}

local function normalizeCounter(counters, key)
    local value = type(counters) == "table" and counters[key] or nil
    if type(value) ~= "number" then
        return "0"
    end

    return tostring(math.max(0, math.floor(value)))
end

local function normalizeAlerts(snapshot)
    local sourceAlerts = type(snapshot) == "table" and snapshot.alerts or nil
    if type(sourceAlerts) ~= "table" then
        return {}
    end

    local alerts = {}
    for _, alert in ipairs(sourceAlerts) do
        if type(alert) == "string" and alert ~= "" then
            alerts[#alerts + 1] = alert
        end
    end

    return alerts
end

function ViewModel.fromSnapshot(snapshot, bridgeStatus)
    snapshot = type(snapshot) == "table" and snapshot or {}
    bridgeStatus = type(bridgeStatus) == "table" and bridgeStatus or {}
    local counters = type(snapshot.counters) == "table" and snapshot.counters or {}

    return {
        title = "AutoFish",
        mode = type(snapshot.mode) == "string" and snapshot.mode or "idle",
        activeProfile = type(snapshot.activeProfile) == "string" and snapshot.activeProfile or "starter-pond",
        remainingBait = tostring(type(snapshot.remainingBait) == "number" and math.max(0, math.floor(snapshot.remainingBait)) or 0),
        freeSlots = tostring(type(snapshot.freeSlots) == "number" and math.max(0, math.floor(snapshot.freeSlots)) or 0),
        bridgeState = bridgeStatus.bridgeOnline and "Online" or "Offline",
        lastAction = type(snapshot.lastAction) == "string" and snapshot.lastAction or "pause",
        lastReason = type(snapshot.lastReason) == "string" and snapshot.lastReason or "view-model generated from incomplete snapshot",
        casts = normalizeCounter(counters, "casts"),
        hooksets = normalizeCounter(counters, "hooksets"),
        catches = normalizeCounter(counters, "catches"),
        skillUps = normalizeCounter(counters, "skillUps"),
        recoveries = normalizeCounter(counters, "recoveries"),
        maintenanceActions = normalizeCounter(counters, "maintenanceActions"),
        alerts = normalizeAlerts(snapshot),
        outboundQueued = tostring(type(bridgeStatus.outboundQueued) == "number" and math.max(0, math.floor(bridgeStatus.outboundQueued)) or 0),
        inboundQueued = tostring(type(bridgeStatus.inboundQueued) == "number" and math.max(0, math.floor(bridgeStatus.inboundQueued)) or 0),
    }
end

AutoFish = AutoFish or {}
AutoFish.UI = AutoFish.UI or {}
AutoFish.UI.ViewModel = ViewModel
if require ~= nil then return ViewModel end
