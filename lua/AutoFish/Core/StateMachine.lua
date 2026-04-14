local Contracts = require("AutoFish.Bridge.Contracts")
local Defaults = require("AutoFish.Core.Defaults")
local Guardrails = require("AutoFish.Core.Guardrails")
local SessionState = require("AutoFish.Core.SessionState")
local SnapshotBuilder = require("AutoFish.Core.SnapshotBuilder")

local StateMachine = {}
StateMachine.__index = StateMachine

function StateMachine.new(config)
    local self = setmetatable({}, StateMachine)
    self.config = Defaults.normalize(config)
    self.session = SessionState.create(self.config, "starter-pond")
    self.lastObservation = nil
    return self
end

function StateMachine:updateConfig(config)
    self.config = Defaults.normalize(config)
end

function StateMachine:setProfile(profileId)
    if profileId and profileId ~= "" then
        self.session.activeProfile = profileId
    end
end

function StateMachine:applyCommand(command)
    local commandType = command and command.commandType or nil
    if commandType == Contracts.CommandType.START then
        self.session.mode = Contracts.Mode.SCANNING
        self.session.lastAction = Contracts.CommandType.START
        self.session.lastReason = "operator started the in-game controller"
    elseif commandType == Contracts.CommandType.PAUSE then
        self.session.mode = Contracts.Mode.PAUSED
        self.session.lastAction = Contracts.CommandType.PAUSE
        self.session.lastReason = "operator paused the in-game controller"
    elseif commandType == Contracts.CommandType.RESUME then
        self.session.mode = Contracts.Mode.SCANNING
        self.session.lastAction = Contracts.CommandType.RESUME
        self.session.lastReason = "operator resumed the in-game controller"
    elseif commandType == Contracts.CommandType.STOP then
        self.session.mode = Contracts.Mode.IDLE
        self.session.lastAction = Contracts.CommandType.STOP
        self.session.lastReason = "operator stopped the in-game controller"
    elseif commandType == Contracts.CommandType.SYNC_PROFILE then
        self:setProfile(command.profileId)
        self.session.lastAction = Contracts.CommandType.SYNC_PROFILE
        self.session.lastReason = "desktop profile synchronized with the in-game controller"
    end
end

function StateMachine:decide(observation)
    local guardrailDecision = Guardrails.evaluate(observation, self.config)
    if guardrailDecision then
        return guardrailDecision
    end

    if observation.biteDetected then
        return { action = "set_hook", mode = Contracts.Mode.HOOKING, reason = "bite detected" }
    end

    if observation.lootReady then
        return { action = "loot", mode = Contracts.Mode.LOOTING, reason = "loot ready" }
    end

    if not observation.lineCast and observation.canCast and observation.nearWater then
        return { action = "cast_line", mode = Contracts.Mode.CASTING, reason = "ready to cast" }
    end

    return { action = "wait", mode = Contracts.Mode.WAITING_BITE, reason = "waiting for bite or loot event" }
end

function StateMachine:observe(observation)
    self.lastObservation = observation
    local decision = self:decide(observation)
    self.session.mode = decision.mode
    self.session.lastAction = decision.action
    self.session.lastReason = decision.reason

    if decision.action == "cast_line" then
        self.session.counters.casts = self.session.counters.casts + 1
        self.session.remainingBait = math.max(0, self.session.remainingBait - 1)
    elseif decision.action == "set_hook" then
        self.session.counters.hooksets = self.session.counters.hooksets + 1
    elseif decision.action == "loot" then
        self.session.counters.catches = self.session.counters.catches + 1
        self.session.freeSlots = math.max(0, self.session.freeSlots - 1)
        if self.session.counters.catches % 3 == 0 then
            self.session.counters.skillUps = self.session.counters.skillUps + 1
        end
    elseif decision.action == "recover_position" then
        self.session.counters.recoveries = self.session.counters.recoveries + 1
    elseif decision.mode == Contracts.Mode.MAINTENANCE then
        self.session.counters.maintenanceActions = self.session.counters.maintenanceActions + 1
        SessionState.resetMaintenanceResources(self.session, self.config)
    end

    self.session.alerts = self:buildAlerts(observation)
    return decision
end

function StateMachine:buildAlerts(observation)
    local alerts = {}
    if observation.inventoryFull or self.session.freeSlots <= self.config.maintenanceAtFreeSlotsOrBelow then
        table.insert(alerts, "Inventory pressure is high.")
    end
    if not observation.baitAvailable or self.session.remainingBait <= self.config.rebaitAtOrBelow then
        table.insert(alerts, "Bait is low.")
    end
    if self.session.mode == Contracts.Mode.PAUSED then
        table.insert(alerts, "Controller is paused.")
    end
    return alerts
end

function StateMachine:getSnapshot(characterName)
    return SnapshotBuilder.build(self.session, characterName, self.lastObservation)
end

function StateMachine:setBridgeOnline(isOnline)
    self.session.bridgeOnline = isOnline == true
end

return StateMachine
