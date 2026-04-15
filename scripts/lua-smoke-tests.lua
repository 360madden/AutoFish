package.path = "lua/?.lua;lua/?/init.lua;lua/?/?.lua;" .. package.path

local Addon = require("AutoFish.AutoFishAddon")

local function fail(message)
    error(message, 2)
end

local function assertEqual(actual, expected, message)
    if actual ~= expected then
        fail(string.format("%s (expected %s, got %s)", message, tostring(expected), tostring(actual)))
    end
end

local function assertContains(values, expected, message)
    for _, value in ipairs(values or {}) do
        if value == expected then
            return
        end
    end

    fail(message .. " (missing '" .. tostring(expected) .. "')")
end

local function makeObservation(overrides)
    local observation = {
        timestamp = 0,
        characterName = "Tester",
        inGame = true,
        nearWater = true,
        inCombat = false,
        inventoryFull = false,
        baitAvailable = true,
        biteDetected = false,
        lootReady = false,
        lineCast = false,
        canCast = true,
    }

    for key, value in pairs(overrides or {}) do
        observation[key] = value
    end

    return observation
end

do
    local addon = Addon.new({}, {})
    addon:applyProfile({
        id = "profile-parity",
        pacing = {
            reactionFloorMs = 100,
            reactionCeilingMs = 200,
            biteTimeoutMs = 9000,
            lootTimeoutMs = 1200,
        },
        thresholds = {
            rebaitAtOrBelow = 2,
            maintenanceAtFreeSlotsOrBelow = 1,
            maxRecoveryAttempts = 2,
        },
        guardrails = {
            pauseOnCombat = false,
            pauseOnBridgeLoss = true,
            recoverOnDrift = true,
        },
    })

    assertEqual(addon.stateMachine.config.reactionFloorMs, 100, "profile pacing should update reactionFloorMs")
    assertEqual(addon.stateMachine.config.reactionCeilingMs, 200, "profile pacing should update reactionCeilingMs")
    assertEqual(addon.stateMachine.config.biteTimeoutMs, 9000, "profile pacing should update biteTimeoutMs")
    assertEqual(addon.stateMachine.config.lootTimeoutMs, 1200, "profile pacing should update lootTimeoutMs")
    assertEqual(addon.stateMachine.config.maxRecoveryAttempts, 2, "profile thresholds should update maxRecoveryAttempts")
    assertEqual(addon.stateMachine.config.pauseOnBridgeLoss, true, "profile guardrails should update pauseOnBridgeLoss")
end

do
    local addon = Addon.new({}, {})
    addon:applyProfile({
        id = "bridge-loss",
        pacing = {
            reactionFloorMs = 50,
            reactionCeilingMs = 50,
            biteTimeoutMs = 1000,
            lootTimeoutMs = 1000,
        },
        thresholds = {
            rebaitAtOrBelow = 1,
            maintenanceAtFreeSlotsOrBelow = 1,
            maxRecoveryAttempts = 2,
        },
        guardrails = {
            pauseOnCombat = true,
            pauseOnBridgeLoss = true,
            recoverOnDrift = true,
        },
    })

    addon:setBridgeOnline(true, "2026-04-14T00:00:00Z")
    addon:onObservation(makeObservation({ timestamp = 0.0 }))
    addon:setBridgeOnline(false, "2026-04-14T00:00:05Z")
    local decision, viewModel = addon:onObservation(makeObservation({ timestamp = 0.1 }))
    local logs = addon:getLogs()

    assertEqual(decision.action, "pause", "bridge loss should pause the controller when configured")
    assertEqual(viewModel.bridgeState, "Offline", "view model should reflect bridge loss")
    assertContains(viewModel.alerts, "Bridge connection is offline.", "bridge-loss alert should be surfaced")
    assertContains(
        (function()
            local messages = {}
            for _, entry in ipairs(logs) do
                messages[#messages + 1] = entry.message
            end
            return messages
        end)(),
        "Guardrail triggered.",
        "guardrail activations should be logged")
end

do
    local addon = Addon.new({}, {})
    addon:applyProfile({
        id = "reaction-window",
        pacing = {
            reactionFloorMs = 100,
            reactionCeilingMs = 200,
            biteTimeoutMs = 1000,
            lootTimeoutMs = 1000,
        },
        thresholds = {
            rebaitAtOrBelow = 1,
            maintenanceAtFreeSlotsOrBelow = 1,
            maxRecoveryAttempts = 2,
        },
        guardrails = {
            pauseOnCombat = true,
            pauseOnBridgeLoss = false,
            recoverOnDrift = true,
        },
    })

    local waitingDecision = addon:onObservation(makeObservation({
        timestamp = 1.0,
        lineCast = true,
        biteDetected = true,
        canCast = false,
    }))
    assertEqual(waitingDecision.action, "wait", "bite detection should honor the reaction floor before hookset")

    local hookDecision = addon:onObservation(makeObservation({
        timestamp = 1.16,
        lineCast = true,
        biteDetected = true,
        canCast = false,
    }))
    assertEqual(hookDecision.action, "set_hook", "bite detection should hook after the reaction window")
end

do
    local addon = Addon.new({}, {})
    addon:applyProfile({
        id = "recovery-limit",
        pacing = {
            reactionFloorMs = 50,
            reactionCeilingMs = 50,
            biteTimeoutMs = 1000,
            lootTimeoutMs = 1000,
        },
        thresholds = {
            rebaitAtOrBelow = 1,
            maintenanceAtFreeSlotsOrBelow = 1,
            maxRecoveryAttempts = 2,
        },
        guardrails = {
            pauseOnCombat = true,
            pauseOnBridgeLoss = false,
            recoverOnDrift = true,
        },
    })

    local recoveryOne = addon:onObservation(makeObservation({ timestamp = 2.0, nearWater = false, canCast = false }))
    local recoveryTwo = addon:onObservation(makeObservation({ timestamp = 2.1, nearWater = false, canCast = false }))
    local recoveryLimit = addon:onObservation(makeObservation({ timestamp = 2.2, nearWater = false, canCast = false }))

    assertEqual(recoveryOne.action, "recover_position", "first drift should attempt recovery")
    assertEqual(recoveryTwo.action, "recover_position", "second drift should still attempt recovery")
    assertEqual(recoveryLimit.action, "pause", "recovery limit should pause after maxRecoveryAttempts is reached")
end

do
    local addon = Addon.new({}, {})
    local decision, viewModel = addon:onObservation({
        timestamp = 3.0,
        character_name = "SnakeCaseTester",
        in_game = true,
        near_water = true,
        in_combat = false,
        inventory_full = false,
        bait_available = true,
        bite_detected = false,
        loot_window_open = false,
        line_cast = false,
        can_cast = true,
    })

    assertEqual(decision.action, "cast_line", "snake_case observations should be accepted")
    assertEqual(viewModel.activeProfile, "starter-pond", "view model should still build from snake_case observations")
end

do
    local addon = Addon.new({}, {})
    local _, viewModel = addon:onObservation(makeObservation({ timestamp = 3.5 }))
    local outbound = addon:drainOutboundMessages()
    local sessionEnvelope = outbound[1]

    assertEqual(sessionEnvelope.messageType, "session_status", "first outbound message should be a session status envelope")
    assertEqual(type(sessionEnvelope.payload.updatedAtUtc), "string", "session status payloads should include updatedAtUtc")
    assertEqual(viewModel.outboundQueued, "2", "view-model queue counts should reflect newly enqueued outbound messages")
    assertEqual(viewModel.inboundQueued, "0", "view-model queue counts should reflect drained inbound commands")
end

do
    local callbackDecisionAction = nil
    local callbackMode = nil
    local addon = Addon.new({}, {
        onDecision = function(decision, viewModel)
            callbackDecisionAction = decision and decision.action or nil
            callbackMode = viewModel and viewModel.mode or nil
        end,
    })

    local decision, viewModel = addon:onObservation(makeObservation({ timestamp = 3.75 }))

    assertEqual(callbackDecisionAction, decision.action, "adapter.onDecision should receive the decision as the first callback argument")
    assertEqual(callbackMode, viewModel.mode, "adapter.onDecision should receive the view-model as the second callback argument")
end

do
    local addon = Addon.new({}, {})
    local queued = addon:queueIntent("not_a_real_intent", nil, "bad intent")
    local logs = addon:getLogs()

    assertEqual(queued, false, "queueIntent should reject invalid intents")
    assertContains(
        (function()
            local messages = {}
            for _, entry in ipairs(logs) do
                messages[#messages + 1] = entry.message
            end
            return messages
        end)(),
        "Rejected queueIntent request.",
        "invalid queueIntent requests should be logged")
end

do
    local addon = Addon.new({}, {})
    local queued = addon:queueCommand("request_snapshot", nil, "snapshot please")
    local decision = addon:onObservation(makeObservation({ timestamp = 3.8 }))
    local logs = addon:getLogs()
    local sawUnsupportedWarning = false

    assertEqual(queued, true, "queueCommand should accept request_snapshot commands")
    assertEqual(decision.action, "cast_line", "request_snapshot should not break the normal observation decision flow")

    for _, entry in ipairs(logs) do
        if entry.message == "Inbound command was normalized but not applied." then
            sawUnsupportedWarning = true
            break
        end
    end

    assertEqual(sawUnsupportedWarning, false, "request_snapshot should be treated as a supported inbound command")
end

do
    local addon = Addon.new({}, {})
    local queued = addon:queueCommand("ack", nil, "acknowledged")
    local decision = addon:onObservation(makeObservation({ timestamp = 3.85 }))
    local logs = addon:getLogs()
    local sawUnsupportedWarning = false

    assertEqual(queued, true, "queueCommand should accept ack commands")
    assertEqual(decision.action, "cast_line", "ack commands should not break the normal observation decision flow")

    for _, entry in ipairs(logs) do
        if entry.message == "Inbound command was normalized but not applied." then
            sawUnsupportedWarning = true
            break
        end
    end

    assertEqual(sawUnsupportedWarning, false, "ack should be treated as a supported inbound command")
end

do
    local adapterCalls = 0
    local addon = Addon.new({}, {
        onDecision = function()
            adapterCalls = adapterCalls + 1
            error("adapter callback exploded")
        end,
    })

    local decision = addon:onObservation(makeObservation({ timestamp = 4.0 }))
    local logs = addon:getLogs()

    assertEqual(decision.action, "cast_line", "adapter callback failures should not break addon observation handling")
    assertEqual(adapterCalls, 1, "adapter callback should still be attempted once")
    assertContains(
        (function()
            local messages = {}
            for _, entry in ipairs(logs) do
                messages[#messages + 1] = entry.message
            end
            return messages
        end)(),
        "adapter.onDecision failed.",
        "adapter callback failures should be logged")
end

do
    local addon = Addon.new({}, {})
    local queued = addon:queueCommand("invalid_command_type", nil, "bad command")
    local logs = addon:getLogs()

    assertEqual(queued, false, "queueCommand should reject invalid command types")
    assertContains(
        (function()
            local messages = {}
            for _, entry in ipairs(logs) do
                messages[#messages + 1] = entry.message
            end
            return messages
        end)(),
        "Rejected queueCommand request.",
        "invalid queueCommand requests should be logged")
end

do
    local addon = Addon.new({}, {})
    local decision = addon:onObservation("not a table")
    local logs = addon:getLogs()

    assertEqual(decision.action, "pause", "non-table observations should fail safe instead of crashing")
    assertContains(
        (function()
            local messages = {}
            for _, entry in ipairs(logs) do
                messages[#messages + 1] = entry.message
            end
            return messages
        end)(),
        "onObservation received a non-table payload; using an empty observation instead.",
        "non-table observations should be logged")
end

do
    local ViewModel = require("AutoFish.UI.ViewModel")
    local snapshot = ViewModel.fromSnapshot(nil, { bridgeOnline = true, outboundQueued = 3 })

    assertEqual(snapshot.bridgeState, "Online", "view-model projection should tolerate nil snapshots")
    assertEqual(snapshot.outboundQueued, "3", "view-model projection should preserve valid queue counts")
    assertEqual(snapshot.inboundQueued, "0", "view-model projection should default missing queue counts")
end

do
    local addon = Addon.new({}, {})
    addon:onObservation(makeObservation({ timestamp = 5.0 }))
    local logs = addon:getLogs()
    local sawDecisionUpdate = false

    for _, entry in ipairs(logs) do
        if entry.message == "Controller decision updated." then
            sawDecisionUpdate = true
            break
        end
    end

    assertEqual(sawDecisionUpdate, true, "state-machine decision transitions should be logged")
end

print("lua smoke ok")
