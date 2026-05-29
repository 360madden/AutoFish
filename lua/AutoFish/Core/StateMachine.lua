local Contracts = AutoFish.Bridge.Contracts
local DecisionRules = AutoFish.Core.DecisionRules
local Defaults = AutoFish.Core.Defaults
local Guardrails = AutoFish.Core.Guardrails
local Observation = AutoFish.Core.Observation
local SessionState = AutoFish.Core.SessionState
local SnapshotBuilder = AutoFish.Core.SnapshotBuilder

local StateMachine = {}
StateMachine.__index = StateMachine

local function resolveTimestampMs(observation)
    local timestamp = Observation.number(observation, "timestamp", nil)
    if type(timestamp) ~= "number" then
        return math.floor(os.clock() * 1000)
    end

    if timestamp >= 100000000000 then
        return math.floor(timestamp)
    end

    return math.floor(timestamp * 1000)
end

local function getReactionDelayMs(config)
    if config.reactionCeilingMs <= config.reactionFloorMs then
        return config.reactionFloorMs
    end

    return math.floor((config.reactionFloorMs + config.reactionCeilingMs) / 2)
end

local function getElapsedMs(timestampMs, startedAtMs)
    if type(timestampMs) ~= "number" or type(startedAtMs) ~= "number" then
        return 0
    end

    return math.max(0, timestampMs - startedAtMs)
end

local function normalizeContext(context)
    if type(context) ~= "table" then
        return nil
    end

    local normalized = {}
    for key, value in pairs(context) do
        local valueType = type(value)
        if valueType == "string" or valueType == "number" or valueType == "boolean" then
            normalized[key] = value
        end
    end

    return normalized
end

local function logIfAvailable(self, level, message, context)
    if not self.logger or type(self.logger[level]) ~= "function" then
        return
    end

    self.logger[level](self.logger, message, normalizeContext(context))
end

function StateMachine.new(config, logger)
    local self = setmetatable({}, StateMachine)
    self.config = Defaults.normalize(config)
    self.session = SessionState.create(self.config, "starter-pond")
    self.lastObservation = nil
    self.lastLoggedDecisionSignature = nil
    self.logger = logger
    return self
end

function StateMachine:updateConfig(config)
    self.config = Defaults.normalize(config)
    logIfAvailable(self, "info", "Controller runtime configuration updated.", {
        reactionFloorMs = self.config.reactionFloorMs,
        reactionCeilingMs = self.config.reactionCeilingMs,
        biteTimeoutMs = self.config.biteTimeoutMs,
        lootTimeoutMs = self.config.lootTimeoutMs,
        maxRecoveryAttempts = self.config.maxRecoveryAttempts,
    })
end

function StateMachine:setProfile(profileId)
    if profileId and profileId ~= "" then
        self.session.activeProfile = profileId
        logIfAvailable(self, "info", "Controller profile changed.", {
            profileId = profileId,
        })
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
    elseif commandType == Contracts.CommandType.REQUEST_SNAPSHOT then
        self.session.lastAction = Contracts.CommandType.REQUEST_SNAPSHOT
        self.session.lastReason = "snapshot requested by operator"
    elseif commandType == Contracts.CommandType.ACK then
        self.session.lastAction = Contracts.CommandType.ACK
        self.session.lastReason = "bridge acknowledgement received"
    else
        logIfAvailable(self, "warn", "Ignored unsupported controller command.", {
            commandType = commandType,
        })
        return false, "command type is not supported by the state machine"
    end

    logIfAvailable(self, "info", "Controller command applied.", {
        commandType = commandType,
        activeProfile = self.session.activeProfile,
        mode = self.session.mode,
    })
    return true, nil
end

function StateMachine:decide(observation)
    local timestampMs = resolveTimestampMs(observation)
    local reactionDelayMs = getReactionDelayMs(self.config)
    local biteDetected = Observation.boolean(observation, "biteDetected", false)
    local lootReady = Observation.boolean(observation, "lootReady", false)
    local lineCast = Observation.boolean(observation, "lineCast", false)
    local canCast = Observation.boolean(observation, "canCast", false)
    local nearWater = Observation.boolean(observation, "nearWater", false)

    if lineCast then
        self.session.lineCastSinceMs = self.session.lineCastSinceMs or timestampMs
    else
        self.session.lineCastSinceMs = nil
    end

    if biteDetected then
        self.session.biteDetectedSinceMs = self.session.biteDetectedSinceMs or timestampMs
    else
        self.session.biteDetectedSinceMs = nil
    end

    if lootReady then
        self.session.lootReadySinceMs = self.session.lootReadySinceMs or timestampMs
    else
        self.session.lootReadySinceMs = nil
    end

    local guardrailDecision = Guardrails.evaluate(observation, self.config, self.session, self.logger)
    if guardrailDecision then
        return guardrailDecision, timestampMs
    end

    local decision = DecisionRules.evaluate({
        config = self.config,
        reactionDelayMs = reactionDelayMs,
        lootReady = lootReady,
        biteDetected = biteDetected,
        lineCast = lineCast,
        canCast = canCast,
        nearWater = nearWater,
        lootReadyForMs = getElapsedMs(timestampMs, self.session.lootReadySinceMs),
        biteDetectedForMs = getElapsedMs(timestampMs, self.session.biteDetectedSinceMs),
        lineCastForMs = getElapsedMs(timestampMs, self.session.lineCastSinceMs),
    })

    if decision then
        return decision, timestampMs
    end

    return { action = "wait", mode = Contracts.Mode.WAITING_BITE, reason = "waiting for bite or loot event" }, timestampMs
end

function StateMachine:observe(observation)
    self.lastObservation = observation
    local decision, timestampMs = self:decide(observation)
    self.session.mode = decision.mode
    self.session.lastAction = decision.action
    self.session.lastReason = decision.reason

    if decision.action == "cast_line" then
        self.session.counters.casts = self.session.counters.casts + 1
        self.session.remainingBait = math.max(0, self.session.remainingBait - 1)
        self.session.recoveryAttempts = 0
        self.session.lineCastSinceMs = timestampMs
        self.session.biteDetectedSinceMs = nil
        self.session.lootReadySinceMs = nil
    elseif decision.action == "set_hook" then
        self.session.counters.hooksets = self.session.counters.hooksets + 1
        self.session.recoveryAttempts = 0
        self.session.biteDetectedSinceMs = nil
    elseif decision.action == "loot" then
        self.session.counters.catches = self.session.counters.catches + 1
        self.session.freeSlots = math.max(0, self.session.freeSlots - 1)
        self.session.recoveryAttempts = 0
        self.session.lineCastSinceMs = nil
        self.session.biteDetectedSinceMs = nil
        self.session.lootReadySinceMs = nil
        if self.session.counters.catches % 3 == 0 then
            self.session.counters.skillUps = self.session.counters.skillUps + 1
        end
    elseif decision.action == "recover_position" then
        self.session.counters.recoveries = self.session.counters.recoveries + 1
        self.session.recoveryAttempts = self.session.recoveryAttempts + 1
    elseif decision.mode == Contracts.Mode.PAUSED then
        self.session.biteDetectedSinceMs = nil
        self.session.lootReadySinceMs = nil
    elseif decision.mode == Contracts.Mode.MAINTENANCE then
        self.session.counters.maintenanceActions = self.session.counters.maintenanceActions + 1
        self.session.recoveryAttempts = 0
        SessionState.resetMaintenanceResources(self.session, self.config)
    end

    self.session.alerts = self:buildAlerts(observation, timestampMs)
    local decisionSignature = table.concat({
        tostring(decision.mode or ""),
        tostring(decision.action or ""),
        tostring(decision.reason or ""),
    }, "|")
    if decisionSignature ~= self.lastLoggedDecisionSignature then
        logIfAvailable(self, "info", "Controller decision updated.", {
            mode = decision.mode,
            action = decision.action,
            reason = decision.reason,
            ruleId = decision.ruleId,
            activeProfile = self.session.activeProfile,
        })
        self.lastLoggedDecisionSignature = decisionSignature
    end

    return decision
end

function StateMachine:buildAlerts(observation, timestampMs)
    local alerts = {}
    if Observation.boolean(observation, "inventoryFull", false) or self.session.freeSlots <= self.config.maintenanceAtFreeSlotsOrBelow then
        table.insert(alerts, "Inventory pressure is high.")
    end
    if not Observation.boolean(observation, "baitAvailable", false) or self.session.remainingBait <= self.config.rebaitAtOrBelow then
        table.insert(alerts, "Bait is low.")
    end
    if self.session.mode == Contracts.Mode.PAUSED then
        table.insert(alerts, "Controller is paused.")
    end
    if self.session.bridgeWasOnline and not self.session.bridgeOnline and self.config.pauseOnBridgeLoss then
        table.insert(alerts, "Bridge connection is offline.")
    end
    if self.session.lastReason == "drift recovery limit reached"
        or (self.config.maxRecoveryAttempts > 0 and self.session.recoveryAttempts >= self.config.maxRecoveryAttempts)
    then
        table.insert(alerts, "Recovery limit reached.")
    end
    if type(self.session.lineCastSinceMs) == "number" and (timestampMs - self.session.lineCastSinceMs) >= self.config.biteTimeoutMs then
        table.insert(alerts, "Bite timeout exceeded for the current cast.")
    end
    return alerts
end

function StateMachine:getSnapshot(characterName)
    return SnapshotBuilder.build(self.session, characterName, self.lastObservation)
end

function StateMachine:setBridgeOnline(isOnline)
    self.session.bridgeOnline = isOnline == true
    if self.session.bridgeOnline then
        self.session.bridgeWasOnline = true
    end
end

function StateMachine:failSafePause(reason)
    local safeReason = type(reason) == "string" and reason ~= "" and reason or "fail-safe pause triggered"

    self.session.mode = Contracts.Mode.PAUSED
    self.session.lastAction = Contracts.CommandType.PAUSE
    self.session.lastReason = safeReason
    self.session.lineCastSinceMs = nil
    self.session.biteDetectedSinceMs = nil
    self.session.lootReadySinceMs = nil
    self.session.alerts = {
        "Controller is paused.",
        "Fail-safe pause was triggered.",
    }
    logIfAvailable(self, "error", "Controller entered fail-safe pause.", {
        reason = safeReason,
    })

    return {
        action = Contracts.CommandType.PAUSE,
        mode = Contracts.Mode.PAUSED,
        reason = safeReason,
    }
end

AutoFish = AutoFish or {}
AutoFish.Core = AutoFish.Core or {}
AutoFish.Core.StateMachine = StateMachine
if require ~= nil then return StateMachine end
