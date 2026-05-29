local Contracts = AutoFish.Bridge.Contracts
local CommandNormalizer = AutoFish.Bridge.CommandNormalizer
local EnvelopeBuilder = AutoFish.Bridge.EnvelopeBuilder
local MessageBus = AutoFish.Bridge.MessageBus
local Logger = AutoFish.Core.Logger
local Observation = AutoFish.Core.Observation
local ProfileRuntime = AutoFish.Core.ProfileRuntime
local StateMachine = AutoFish.Core.StateMachine
local Layout = AutoFish.UI.Layout
local UIController = AutoFish.UI.Controller
local ViewModel = AutoFish.UI.ViewModel

local AutoFishAddon = {}
AutoFishAddon.__index = AutoFishAddon

local function normalizeObservation(addon, observation)
    if type(observation) == "table" then
        return observation
    end

    addon.logger:warn("onObservation received a non-table payload; using an empty observation instead.", {
        observationType = type(observation),
    })
    return {}
end

local function buildFallbackBridgeStatus(bridgeStatus)
    bridgeStatus = type(bridgeStatus) == "table" and bridgeStatus or {}

    return {
        bridgeOnline = bridgeStatus.bridgeOnline == true,
        lastHeartbeatUtc = type(bridgeStatus.lastHeartbeatUtc) == "string" and bridgeStatus.lastHeartbeatUtc or nil,
        outboundQueued = type(bridgeStatus.outboundQueued) == "number" and bridgeStatus.outboundQueued or 0,
        inboundQueued = type(bridgeStatus.inboundQueued) == "number" and bridgeStatus.inboundQueued or 0,
    }
end

local function buildFallbackSnapshot(addon, characterName, reason)
    local session = addon.stateMachine and addon.stateMachine.session or {}
    local counters = session.counters or {}
    local alerts = type(session.alerts) == "table" and session.alerts or {}
    local fallbackAlerts = {}

    for _, alert in ipairs(alerts) do
        fallbackAlerts[#fallbackAlerts + 1] = alert
    end

    fallbackAlerts[#fallbackAlerts + 1] = reason

    return {
        characterName = characterName or "Unknown",
        activeProfile = type(session.activeProfile) == "string" and session.activeProfile or "starter-pond",
        mode = type(session.mode) == "string" and session.mode or Contracts.Mode.PAUSED,
        inGame = false,
        nearWater = false,
        inCombat = false,
        inventoryFull = false,
        bridgeOnline = session.bridgeOnline == true,
        remainingBait = type(session.remainingBait) == "number" and session.remainingBait or 0,
        freeSlots = type(session.freeSlots) == "number" and session.freeSlots or 0,
        lastAction = type(session.lastAction) == "string" and session.lastAction or Contracts.CommandType.PAUSE,
        lastReason = type(session.lastReason) == "string" and session.lastReason or reason,
        updatedAtUtc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
        counters = {
            casts = type(counters.casts) == "number" and counters.casts or 0,
            hooksets = type(counters.hooksets) == "number" and counters.hooksets or 0,
            catches = type(counters.catches) == "number" and counters.catches or 0,
            skillUps = type(counters.skillUps) == "number" and counters.skillUps or 0,
            recoveries = type(counters.recoveries) == "number" and counters.recoveries or 0,
            maintenanceActions = type(counters.maintenanceActions) == "number" and counters.maintenanceActions or 0,
        },
        alerts = fallbackAlerts,
    }
end

local function buildFallbackViewModel(snapshot, bridgeStatus)
    local counters = type(snapshot.counters) == "table" and snapshot.counters or {}

    return {
        title = "AutoFish",
        mode = snapshot.mode or Contracts.Mode.PAUSED,
        activeProfile = snapshot.activeProfile or "starter-pond",
        remainingBait = tostring(snapshot.remainingBait or 0),
        freeSlots = tostring(snapshot.freeSlots or 0),
        bridgeState = bridgeStatus.bridgeOnline and "Online" or "Offline",
        lastAction = snapshot.lastAction or Contracts.CommandType.PAUSE,
        lastReason = snapshot.lastReason or "fallback view-model generated",
        casts = tostring(counters.casts or 0),
        hooksets = tostring(counters.hooksets or 0),
        catches = tostring(counters.catches or 0),
        skillUps = tostring(counters.skillUps or 0),
        recoveries = tostring(counters.recoveries or 0),
        maintenanceActions = tostring(counters.maintenanceActions or 0),
        alerts = type(snapshot.alerts) == "table" and snapshot.alerts or {},
        outboundQueued = tostring(bridgeStatus.outboundQueued or 0),
        inboundQueued = tostring(bridgeStatus.inboundQueued or 0),
    }
end

local function buildLogger(adapter)
    local safeAdapter = type(adapter) == "table" and adapter or {}

    return Logger.new({
        maxEntries = safeAdapter.logCapacity,
        sink = type(safeAdapter.onLog) == "function" and function(entry)
            safeAdapter.onLog(entry)
        end or nil,
    })
end

function AutoFishAddon.new(config, adapter)
    local logger = buildLogger(adapter)
    local safeConfig = config
    local safeAdapter = adapter

    if safeConfig ~= nil and type(safeConfig) ~= "table" then
        logger:warn("AutoFishAddon.new received a non-table config; using defaults instead.", {
            configType = type(safeConfig),
        })
        safeConfig = {}
    end

    if safeAdapter ~= nil and type(safeAdapter) ~= "table" then
        logger:warn("AutoFishAddon.new received a non-table adapter; using an empty adapter instead.", {
            adapterType = type(safeAdapter),
        })
        safeAdapter = {}
    end

    local self = setmetatable({}, AutoFishAddon)
    self.logger = logger
    self.config = safeConfig or {}
    self.adapter = safeAdapter or {}
    self.bus = MessageBus.new(self.logger)
    self.stateMachine = StateMachine.new(self.config, self.logger)
    self.currentViewModel = nil
    self.logger:info("AutoFish addon initialized.", {
        activeProfile = self.stateMachine.session.activeProfile,
    })
    return self
end

function AutoFishAddon:getLayout()
    return Layout
end

function AutoFishAddon:getLogs()
    return self.logger:getEntries()
end

function AutoFishAddon:clearLogs()
    self.logger:clear()
end

function AutoFishAddon:setBridgeOnline(isOnline, heartbeatUtc)
    local previousStatus = self.bus:getStatus()
    self.bus:setBridgeOnline(isOnline, heartbeatUtc)
    self.stateMachine:setBridgeOnline(isOnline)

    local isOnlineNow = isOnline == true
    if previousStatus.bridgeOnline ~= isOnlineNow then
        self.logger:info("Bridge connectivity changed.", {
            bridgeOnline = isOnlineNow,
            heartbeatUtc = heartbeatUtc,
        })
    end
end

function AutoFishAddon:handleInboundCommands()
    local commands = self.bus:drainInbound()
    if type(commands) ~= "table" then
        self.logger:error("Inbound queue drain returned a non-table value; inbound commands were dropped.")
        return 0
    end

    local processedCount = 0
    for _, command in ipairs(commands) do
        local normalized, reason = CommandNormalizer.normalize(command)
        if normalized then
            local ok, applied, applyError = pcall(self.stateMachine.applyCommand, self.stateMachine, normalized)
            if ok and applied ~= false then
                processedCount = processedCount + 1
            elseif ok then
                self.logger:warn("Inbound command was normalized but not applied.", {
                    commandType = normalized.commandType,
                    reason = applyError,
                })
            else
                self.logger:error("Inbound command application failed; switching to fail-safe pause.", {
                    commandType = normalized.commandType,
                    error = applied,
                })
                self.stateMachine:failSafePause("command handling failed after an internal error")
            end
        else
            self.logger:warn("Discarded inbound command.", {
                reason = reason,
            })
        end
    end

    return processedCount
end

function AutoFishAddon:onObservation(observation)
    local safeObservation = normalizeObservation(self, observation)
    local characterName = Observation.string(safeObservation, "characterName", "Unknown")

    local inboundOk, inboundError = pcall(self.handleInboundCommands, self)
    if not inboundOk then
        self.logger:error("Inbound command handling failed; switching to fail-safe pause.", {
            error = inboundError,
        })
        self.stateMachine:failSafePause("inbound command handling failed")
    end

    local observeOk, decision = pcall(self.stateMachine.observe, self.stateMachine, safeObservation)
    if not observeOk or type(decision) ~= "table" then
        self.logger:error("State machine observation handling failed; switching to fail-safe pause.", {
            error = observeOk and "observe returned a non-table decision" or decision,
        })
        decision = self.stateMachine:failSafePause("controller observe failed")
    end

    local snapshotOk, snapshot = pcall(self.stateMachine.getSnapshot, self.stateMachine, characterName)
    if not snapshotOk or type(snapshot) ~= "table" then
        self.logger:error("Snapshot build failed; using fallback snapshot.", {
            error = snapshot,
        })
        snapshot = buildFallbackSnapshot(self, characterName, "snapshot build failed")
    end

    local sessionEnvelope, sessionEnvelopeError = EnvelopeBuilder.buildSessionStatus(snapshot)
    if sessionEnvelope then
        if not self.bus:enqueueOutbound(sessionEnvelope) then
            self.logger:error("Session status envelope enqueue failed.")
        end
    else
        self.logger:error("Session status envelope build failed.", {
            error = sessionEnvelopeError,
        })
    end

    local ackEnvelope, ackEnvelopeError = EnvelopeBuilder.buildAck(decision)
    if ackEnvelope then
        if not self.bus:enqueueOutbound(ackEnvelope) then
            self.logger:error("Acknowledgement envelope enqueue failed.")
        end
    else
        self.logger:error("Acknowledgement envelope build failed.", {
            error = ackEnvelopeError,
        })
    end

    local bridgeStatus = buildFallbackBridgeStatus(self.bus:getStatus())
    local viewModelOk, viewModel = pcall(ViewModel.fromSnapshot, snapshot, bridgeStatus)
    if not viewModelOk or type(viewModel) ~= "table" then
        self.logger:error("View-model projection failed; using fallback view-model.", {
            error = viewModel,
        })
        viewModel = buildFallbackViewModel(snapshot, bridgeStatus)
    end

    self.currentViewModel = viewModel

    if self.adapter.onDecision then
        local callbackOk, callbackError = pcall(self.adapter.onDecision, decision, self.currentViewModel)
        if not callbackOk then
            self.logger:error("adapter.onDecision failed.", {
                error = callbackError,
            })
        end
    end

    return decision, self.currentViewModel
end

function AutoFishAddon:applyProfile(profile)
    if profile ~= nil and type(profile) ~= "table" then
        self.logger:warn("applyProfile received a non-table payload; using normalized defaults instead.", {
            profileType = type(profile),
        })
    end

    local runtimeConfig = ProfileRuntime.fromProfile(profile)
    self.config = runtimeConfig
    self.stateMachine:updateConfig(runtimeConfig)
    if type(profile) == "table" and type(profile.id) == "string" then
        self.stateMachine:setProfile(profile.id)
        self.logger:info("Profile applied to the addon runtime.", {
            profileId = profile.id,
        })
    end
end

function AutoFishAddon:queueCommand(commandType, profileId, notes)
    local command, reason = CommandNormalizer.normalize({
        commandType = commandType,
        issuedAtUtc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
        profileId = profileId,
        notes = notes,
    })
    if command then
        if self.bus:enqueueInbound(command) then
            return true
        end

        self.logger:error("queueCommand failed to enqueue a normalized command.", {
            commandType = command.commandType,
        })
        return false
    end

    self.logger:warn("Rejected queueCommand request.", {
        commandType = commandType,
        reason = reason,
    })
    return false
end

function AutoFishAddon:queueIntent(intent, profileId, notes)
    local command, reason = UIController.intentToCommand(intent, profileId, notes)
    if command then
        if self.bus:enqueueInbound(command) then
            return true
        end

        self.logger:error("queueIntent failed to enqueue a normalized command.", {
            intent = intent,
        })
        return false
    end

    self.logger:warn("Rejected queueIntent request.", {
        intent = intent,
        reason = reason,
    })
    return false
end

function AutoFishAddon:drainOutboundMessages()
    local drained = self.bus:drainOutbound()
    if type(drained) ~= "table" then
        self.logger:error("Outbound queue drain returned a non-table value; using an empty list instead.")
        return {}
    end

    return drained
end

AutoFish = AutoFish or {}
AutoFish.AutoFishAddon = AutoFishAddon
if require ~= nil then return AutoFishAddon end
