local Contracts = require("AutoFish.Bridge.Contracts")
local CommandNormalizer = require("AutoFish.Bridge.CommandNormalizer")
local EnvelopeBuilder = require("AutoFish.Bridge.EnvelopeBuilder")
local MessageBus = require("AutoFish.Bridge.MessageBus")
local ProfileRuntime = require("AutoFish.Core.ProfileRuntime")
local StateMachine = require("AutoFish.Core.StateMachine")
local Layout = require("AutoFish.UI.Layout")
local UIController = require("AutoFish.UI.Controller")
local ViewModel = require("AutoFish.UI.ViewModel")

local AutoFishAddon = {}
AutoFishAddon.__index = AutoFishAddon

function AutoFishAddon.new(config, adapter)
    local self = setmetatable({}, AutoFishAddon)
    self.config = config or {}
    self.adapter = adapter or {}
    self.bus = MessageBus.new()
    self.stateMachine = StateMachine.new(config)
    self.currentViewModel = nil
    return self
end

function AutoFishAddon:getLayout()
    return Layout
end

function AutoFishAddon:setBridgeOnline(isOnline, heartbeatUtc)
    self.bus:setBridgeOnline(isOnline, heartbeatUtc)
    self.stateMachine:setBridgeOnline(isOnline)
end

function AutoFishAddon:handleInboundCommands()
    local commands = self.bus:drainInbound()
    for _, command in ipairs(commands) do
        local normalized = CommandNormalizer.normalize(command)
        if normalized then
            self.stateMachine:applyCommand(normalized)
        end
    end
end

function AutoFishAddon:onObservation(observation)
    self:handleInboundCommands()
    local decision = self.stateMachine:observe(observation)
    local snapshot = self.stateMachine:getSnapshot(observation.characterName)
    self.currentViewModel = ViewModel.fromSnapshot(snapshot, self.bus:getStatus())

    self.bus:enqueueOutbound(EnvelopeBuilder.buildSessionStatus(snapshot))
    self.bus:enqueueOutbound(EnvelopeBuilder.buildAck(decision))

    if self.adapter.onDecision then
        self.adapter:onDecision(decision, self.currentViewModel)
    end

    return decision, self.currentViewModel
end

function AutoFishAddon:applyProfile(profile)
    local runtimeConfig = ProfileRuntime.fromProfile(profile)
    self.config = runtimeConfig
    self.stateMachine:updateConfig(runtimeConfig)
    if type(profile) == "table" and type(profile.id) == "string" then
        self.stateMachine:setProfile(profile.id)
    end
end

function AutoFishAddon:queueCommand(commandType, profileId, notes)
    local command = CommandNormalizer.normalize({
        commandType = commandType,
        issuedAtUtc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
        profileId = profileId,
        notes = notes,
    })
    if command then
        self.bus:enqueueInbound(command)
    end
end

function AutoFishAddon:queueIntent(intent, profileId, notes)
    local command = UIController.intentToCommand(intent, profileId, notes)
    if command then
        self.bus:enqueueInbound(command)
    end
end

function AutoFishAddon:drainOutboundMessages()
    return self.bus:drainOutbound()
end

return AutoFishAddon
