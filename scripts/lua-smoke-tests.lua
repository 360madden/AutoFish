package.path = "lua/?.lua;lua/?/init.lua;lua/?/?.lua;" .. package.path

-- Pre-load all AutoFish module dependencies to populate the global AutoFish namespace.
-- In RIFT, these are loaded in order via the .toc manifest. In offline tests, we
-- require them explicitly so that downstream requires referencing AutoFish.* work.
require("AutoFish.Core.Logger")
require("AutoFish.Core.Defaults")
require("AutoFish.Core.Observation")
require("AutoFish.Bridge.Contracts")
require("AutoFish.Bridge.JsonParser")
require("AutoFish.UI.Layout")
require("AutoFish.Core.SessionState")
require("AutoFish.Core.ProfileRuntime")
require("AutoFish.Core.SnapshotBuilder")
require("AutoFish.Bridge.MessageBus")
require("AutoFish.Core.DecisionRules")
require("AutoFish.Bridge.CommandNormalizer")
require("AutoFish.Bridge.EnvelopeBuilder")
require("AutoFish.UI.Controller")
require("AutoFish.Core.GuardrailRules")
require("AutoFish.Core.Guardrails")
require("AutoFish.UI.ViewModel")
require("AutoFish.Core.StateMachine")

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

-- ── jsonToTable parser tests (AutoFish.Bridge.JsonParser) ──────────

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- Empty object
    local result, err = JsonParser.parse("{}")
    assertEqual(type(result), "table", "jsonToTable({}) should return a table")
    assertEqual(#result, 0, "empty object should have no elements")

    -- Nil input
    result, err = JsonParser.parse(nil)
    assertEqual(result, nil, "jsonToTable(nil) should return nil")
    assertEqual(err, "input must be a string", "jsonToTable(nil) error message")

    -- Empty string
    result, err = JsonParser.parse("")
    assertEqual(result, nil, "jsonToTable('') should return nil")
    assertEqual(err, "empty input", "jsonToTable('') error message")

    -- Whitespace-only
    result, err = JsonParser.parse("   \n\t  ")
    assertEqual(result, nil, "jsonToTable('   ') should return nil")
    assertEqual(err, "empty input", "jsonToTable('   ') error message")
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- Simple string value
    local result = JsonParser.parse('{"key": "value"}')
    assertEqual(type(result), "table", "simple object should return a table")
    assertEqual(result.key, "value", "key should be 'value'")

    -- Number value
    result = JsonParser.parse('{"number": 42}')
    assertEqual(result.number, 42, "integer should parse")

    -- Float
    result = JsonParser.parse('{"float": 3.14}')
    assertEqual(result.float, 3.14, "float should parse")

    -- Negative number
    result = JsonParser.parse('{"negative": -7}')
    assertEqual(result.negative, -7, "negative number should parse")

    -- Boolean true
    result = JsonParser.parse('{"flag": true}')
    assertEqual(result.flag, true, "true should parse")

    -- Boolean false
    result = JsonParser.parse('{"flag": false}')
    assertEqual(result.flag, false, "false should parse")

    -- Null (nil in Lua)
    result = JsonParser.parse('{"nothing": null}')
    assertEqual(type(result), "table", "object with null should still parse")
    assertEqual(result.nothing, nil, "null should map to nil")
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- Mixed types in one object
    local result = JsonParser.parse('{"name":"hello","count":10,"ratio":2.5,"active":true,"extra":null}')
    assertEqual(result.name, "hello", "string value in mixed object")
    assertEqual(result.count, 10, "number value in mixed object")
    assertEqual(result.ratio, 2.5, "float value in mixed object")
    assertEqual(result.active, true, "boolean value in mixed object")
    assertEqual(result.extra, nil, "null value in mixed object")
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- Nested objects
    local result = JsonParser.parse('{"outer": {"inner": "deep"}}')
    assertEqual(type(result.outer), "table", "nested object should be a table")
    assertEqual(result.outer.inner, "deep", "nested value should parse")

    -- Deeply nested
    result = JsonParser.parse('{"a":{"b":{"c":{"d":99}}}}')
    assertEqual(result.a.b.c.d, 99, "deeply nested value should parse")
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- Empty array
    local result = JsonParser.parse('[]')
    assertEqual(type(result), "table", "empty array should return a table")
    assertEqual(#result, 0, "empty array should have length 0")

    -- Number array
    result = JsonParser.parse('[1, 2, 3]')
    assertEqual(#result, 3, "array should have correct length")
    assertEqual(result[1], 1, "array[1] should be 1")
    assertEqual(result[2], 2, "array[2] should be 2")
    assertEqual(result[3], 3, "array[3] should be 3")

    -- Mixed array (null maps to nil, which doesn't occupy a table slot)
    result = JsonParser.parse('[1, "two", false, null]')
    assertEqual(#result, 3, "mixed array length excludes trailing nils")
    assertEqual(result[1], 1, "mixed[1]")
    assertEqual(result[2], "two", "mixed[2]")
    assertEqual(result[3], false, "mixed[3]")
    assertEqual(result[4], nil, "mixed[4] = null -> nil")
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- Array of objects
    local result = JsonParser.parse('[{"id":1}, {"id":2}]')
    assertEqual(#result, 2, "array of objects length")
    assertEqual(result[1].id, 1, "array[1].id")
    assertEqual(result[2].id, 2, "array[2].id")

    -- Object containing arrays
    result = JsonParser.parse('{"tags": ["a", "b", "c"]}')
    assertEqual(type(result.tags), "table", "tags should be a table")
    assertEqual(#result.tags, 3, "tags length")
    assertEqual(result.tags[1], "a", "tag[1]")
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- String with escaped quotes
    local result = JsonParser.parse('{"text": "hello \\"world\\""}')
    assertEqual(result.text, 'hello "world"', "escaped quotes should parse")

    -- String with escape sequences
    result = JsonParser.parse('{"text": "line1\\nline2"}')
    assertEqual(result.text, "line1\nline2", "escaped newline should parse")

    -- String with tab
    result = JsonParser.parse('{"text": "col1\\tcol2"}')
    assertEqual(result.text, "col1\tcol2", "escaped tab should parse")

    -- String with slash
    result = JsonParser.parse('{"path": "a\\/b"}')
    assertEqual(result.path, "a/b", "escaped slash should parse")
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- Whitespace handling
    local result = JsonParser.parse('  {  "key"  :  "val"  }  ')
    assertEqual(result.key, "val", "whitespace should be trimmed")

    -- Newlines between tokens
    result = JsonParser.parse('{\n  "a": 1,\n  "b": 2\n}')
    assertEqual(result.a, 1, "multi-line object a")
    assertEqual(result.b, 2, "multi-line object b")
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- Trailing characters (error)
    local result, err = JsonParser.parse('{"a":1} extra')
    assertEqual(result, nil, "trailing chars should error")
    assertEqual(err, "trailing characters after value", "trailing chars error message")

    -- Unterminated string
    result, err = JsonParser.parse('{"a": "unclosed')
    assertEqual(result, nil, "unterminated string should error")

    -- Invalid JSON: single value
    result, err = JsonParser.parse('hello')
    assertEqual(result, nil, "bare word should error")

    -- Missing colon
    result, err = JsonParser.parse('{"a" 1}')
    assertEqual(result, nil, "missing colon should error")

    -- Number parsing edge: decimal with no digits before point
    result = JsonParser.parse('{"v": 0.5}')
    assertEqual(result.v, 0.5, "0.5 should parse")
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- Scientific notation: integer with exponent
    local result = JsonParser.parse('{"v": 1e6}')
    assertEqual(result.v, 1000000.0, "1e6 should parse as 1000000")

    -- Scientific notation: negative exponent
    result = JsonParser.parse('{"v": 1e-3}')
    assertEqual(result.v, 0.001, "1e-3 should parse as 0.001")

    -- Scientific notation: explicit positive exponent
    result = JsonParser.parse('{"v": 5e+2}')
    assertEqual(result.v, 500.0, "5e+2 should parse as 500")

    -- Scientific notation: float with exponent
    result = JsonParser.parse('{"v": 3.14e2}')
    assertEqual(result.v, 314.0, "3.14e2 should parse as 314")

    -- Scientific notation: float with negative exponent
    result = JsonParser.parse('{"v": 1.5e-2}')
    assertEqual(result.v, 0.015, "1.5e-2 should parse as 0.015")

    -- Scientific notation: negative base with exponent
    result = JsonParser.parse('{"v": -3.14e1}')
    assertEqual(result.v, -31.4, "-3.14e1 should parse as -31.4")

    -- Scientific notation: uppercase E
    result = JsonParser.parse('{"v": 2E3}')
    assertEqual(result.v, 2000.0, "2E3 should parse as 2000")

    -- Scientific notation: uppercase E negative
    result = JsonParser.parse('{"v": 2E-3}')
    assertEqual(result.v, 0.002, "2E-3 should parse as 0.002")

    -- Scientific notation: very large number
    result = JsonParser.parse('{"v": 1e10}')
    assertEqual(result.v, 10000000000.0, "1e10 should parse as 10000000000")

    -- Scientific notation: very small number
    result = JsonParser.parse('{"v": 1e-10}')
    assertEqual(result.v, 0.0000000001, "1e-10 should parse as 0.0000000001")

    -- Scientific notation: zero with exponent
    result = JsonParser.parse('{"v": 0.0e0}')
    assertEqual(result.v, 0.0, "0.0e0 should parse as 0")
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- Deeply nested empty arrays
    local result = JsonParser.parse('[[[]]]')
    assertEqual(type(result), "table", "deeply nested empty arrays should parse")
    assertEqual(#result, 1, "outer array length")
    assertEqual(type(result[1]), "table", "middle array type")
    assertEqual(#result[1], 1, "middle array length")
    assertEqual(type(result[1][1]), "table", "inner array type")
    assertEqual(#result[1][1], 0, "inner array length")

    -- Nested arrays with values
    result = JsonParser.parse('[[1, [2, 3]], 4]')
    assertEqual(#result, 2, "nested array outer length")
    assertEqual(type(result[1]), "table", "nested[1] type")
    assertEqual(#result[1], 2, "nested[1] length")
    assertEqual(result[1][1], 1, "nested[1][1]")
    assertEqual(type(result[1][2]), "table", "nested[1][2] type")
    assertEqual(result[1][2][1], 2, "nested[1][2][1]")
    assertEqual(result[1][2][2], 3, "nested[1][2][2]")
    assertEqual(result[2], 4, "nested[2]")

    -- Deeply nested single value
    result = JsonParser.parse('[[[[[42]]]]]')
    assertEqual(result[1][1][1][1][1], 42, "5 levels deep should resolve to 42")

    -- 2D array (matrix) as object value
    result = JsonParser.parse('{"matrix": [[1, 2], [3, 4]]}')
    assertEqual(type(result.matrix), "table", "matrix should be a table")
    assertEqual(#result.matrix, 2, "matrix row count")
    assertEqual(#result.matrix[1], 2, "matrix row 1 length")
    assertEqual(result.matrix[1][1], 1, "matrix[1][1]")
    assertEqual(result.matrix[1][2], 2, "matrix[1][2]")
    assertEqual(result.matrix[2][1], 3, "matrix[2][1]")
    assertEqual(result.matrix[2][2], 4, "matrix[2][2]")

    -- Mixed nested: objects inside arrays inside objects
    result = JsonParser.parse('{"data": [{"id": 1, "vals": [10, 20]}, {"id": 2, "vals": [30]}]}')
    assertEqual(#result.data, 2, "data array length")
    assertEqual(result.data[1].id, 1, "data[1].id")
    assertEqual(#result.data[1].vals, 2, "data[1].vals length")
    assertEqual(result.data[1].vals[1], 10, "data[1].vals[1]")
    assertEqual(result.data[1].vals[2], 20, "data[1].vals[2]")
    assertEqual(result.data[2].id, 2, "data[2].id")
    assertEqual(#result.data[2].vals, 1, "data[2].vals length")
    assertEqual(result.data[2].vals[1], 30, "data[2].vals[1]")

    -- Empty arrays at various depths
    result = JsonParser.parse('{"a": [], "b": [[]], "c": [{}]}')
    assertEqual(type(result.a), "table", "a should be empty array")
    assertEqual(#result.a, 0, "a should have length 0")
    assertEqual(type(result.b), "table", "b should be array")
    assertEqual(#result.b, 1, "b length")
    assertEqual(type(result.b[1]), "table", "b[1] should be empty array")
    assertEqual(#result.b[1], 0, "b[1] length")
    assertEqual(type(result.c), "table", "c should be array")
    assertEqual(#result.c, 1, "c length")
    assertEqual(type(result.c[1]), "table", "c[1] should be empty object")
    assertEqual(#result.c[1], 0, "c[1] should have no keys")
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- 10 levels deep
    local result = JsonParser.parse('{"a":{"b":{"c":{"d":{"e":{"f":{"g":{"h":{"i":{"j":42}}}}}}}}}}')
    assertEqual(result.a.b.c.d.e.f.g.h.i.j, 42, "10 levels deep should resolve")

    -- 20 levels deep (stress the recursive descent parser)
    result = JsonParser.parse('{"a":{"b":{"c":{"d":{"e":{"f":{"g":{"h":{"i":{"j":{"k":{"l":{"m":{"n":{"o":{"p":{"q":{"r":{"s":{"t":true}}}}}}}}}}}}}}}}}}}}')
    assertEqual(result.a.b.c.d.e.f.g.h.i.j.k.l.m.n.o.p.q.r.s.t, true, "20 levels deep should resolve")

    -- Deeply nested object as array element
    result = JsonParser.parse('[{"level1": {"level2": {"level3": [1, 2, 3]}}}]')
    assertEqual(result[1].level1.level2.level3[1], 1, "nested object inside array inside object inside array")
    assertEqual(result[1].level1.level2.level3[2], 2, "path[2]")
    assertEqual(result[1].level1.level2.level3[3], 3, "path[3]")

    -- Object with many keys (wide, not deep)
    result = JsonParser.parse('{"k0":0,"k1":1,"k2":2,"k3":3,"k4":4,"k5":5,"k6":6,"k7":7,"k8":8,"k9":9}')
    for i = 0, 9 do
        local key = "k" .. i
        assertEqual(result[key], i, "wide object key " .. key)
    end

    -- Mixed: array buried 4 levels deep inside objects
    result = JsonParser.parse('{"a":{"b":{"c":{"d":["found"]}}}}')
    assertEqual(result.a.b.c.d[1], "found", "array 4 levels deep inside objects")
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- Basic BMP unicode escape
    local result = JsonParser.parse('{"char": "\\u0041"}')
    assertEqual(result.char, "\\u0041", "\\u0041 should pass through as literal text (Lua 5.1 has no utf8 library)")

    -- Accented character escape
    result = JsonParser.parse('{"char": "\\u00e9"}')
    assertEqual(result.char, "\\u00e9", "\\u00e9 should pass through as literal text")

    -- Unicode symbol escape
    result = JsonParser.parse('{"char": "\\u2603"}')
    assertEqual(result.char, "\\u2603", "\\u2603 (snowman) should pass through as literal text")

    -- Multiple unicode escapes in sequence
    result = JsonParser.parse('{"text": "\\u0048\\u0065\\u006c\\u006c\\u006f"}')
    assertEqual(result.text, "\\u0048\\u0065\\u006c\\u006c\\u006f", "\\u sequences should not crash on consecutive escapes")

    -- Mixed regular text with unicode escape
    result = JsonParser.parse('{"text": "hello\\n\\u0041world"}')
    assertEqual(result.text, "hello\n\\u0041world", "mixed newline and unicode escape should preserve both correctly")

    -- Escape sequence followed by normal unicode escape
    result = JsonParser.parse('{"text": "\\t\\u0042\\n"}')
    assertEqual(result.text, "\t\\u0042\n", "tab + unicode + newline should produce correct escape results")

    -- Single unicode escape by itself (top-level string IS supported by parseValue)
    local parseResult, err = JsonParser.parse('"\\u0041"')
    assertEqual(parseResult, "\\u0041", "bare string with unicode should return the literal text (\\u escapes pass through)")
    assertEqual(err, nil, "bare string should not produce an error")
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- Number beyond Lua's integer precision (2^53 + 1)
    local result = JsonParser.parse('{"v": 9007199254740993}')
    assertEqual(type(result.v), "number", "large integer should still parse as a number")
    -- Lua's tonumber may lose precision for integers beyond 2^53
    -- 9007199254740993 may round to 9007199254740992 in double-precision
    assertEqual(result.v >= 9007199254740992, true, "large integer should be close to original (may round in Lua double)")

    -- Very large exponent
    result = JsonParser.parse('{"v": 1e100}')
    assertEqual(type(result.v), "number", "1e100 should parse as a number")
    assertEqual(result.v == math.huge or result.v > 1e99, true, "1e100 should be very large (may be inf in Lua)")

    -- Very small number (near denormalized)
    result = JsonParser.parse('{"v": 1e-300}')
    assertEqual(type(result.v), "number", "1e-300 should parse as a number")
    assertEqual(result.v > 0, true, "1e-300 should be positive (may underflow to 0 in Lua)")

    -- Number with many decimal places (precision loss expected)
    result = JsonParser.parse('{"v": 3.14159265358979323846}')
    assertEqual(type(result.v), "number", "pi with many decimals should parse")
    -- Double precision gives about 15-17 significant digits
    assertEqual(tostring(result.v):sub(1, 6), "3.1415", "pi should be approximately correct")

    -- Integer at max safe integer range
    result = JsonParser.parse('{"v": 9007199254740991}')
    assertEqual(result.v, 9007199254740991, "2^53 should preserve precision")

    -- Zero with many trailing decimal digits
    result = JsonParser.parse('{"v": 0.000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001}')
    assertEqual(type(result.v), "number", "very small decimal should parse as number")
    assertEqual(result.v >= 0 and result.v < 1e-10, true, "very small decimal should be near zero")
end

-- ── consumeInboundCommands pipeline tests with mock EditBox ──────────
-- These tests exercise the same processing pipeline that consumeInboundCommands()
-- runs: read EditBox text → split lines → JSON parse → normalize →
-- bus:enqueueInbound → handleInboundCommands → sync state → clear EditBox.
-- Since consumeInboundCommands is a local function in Main.lua (not exported),
-- we simulate the pipeline inline using the same imported modules.

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")
    local CommandNormalizer = require("AutoFish.Bridge.CommandNormalizer")
    local Contracts = require("AutoFish.Bridge.Contracts")
    local Addon = require("AutoFish.AutoFishAddon")

    -- Create a mock EditBox that mirrors what ensureBridgeEditBox() produces
    local editBox = {
        text = "",
        getTextCallCount = 0,
        setTextCallCount = 0,
        lastSetText = nil,
        GetText = function(self)
            self.getTextCallCount = self.getTextCallCount + 1
            return self.text
        end,
        SetText = function(self, newText)
            self.setTextCallCount = self.setTextCallCount + 1
            self.lastSetText = newText
        end,
    }

    -- Helper: simulate consumeInboundCommands' processing loop
    local function processInboundText(addon, editBox, stateSession)
        local text = editBox:GetText()
        if type(text) ~= "string" or text == "" then
            return 0
        end

        local enqueuedCount = 0
        for line in string.gmatch(text, "[^\n]+") do
            local trimmed = string.match(line, "^%s*(.-)%s*$")
            if trimmed and trimmed ~= "" then
                local okParse, parsed = pcall(JsonParser.parse, trimmed)
                if okParse and type(parsed) == "table" then
                    local command, reason = CommandNormalizer.normalize(parsed)
                    if command then
                        addon.bus:enqueueInbound(command)
                        enqueuedCount = enqueuedCount + 1
                    end
                end
            end
        end

        if enqueuedCount > 0 then
            addon:handleInboundCommands()

            -- Sync state back (same fields as consumeInboundCommands)
            local sm = addon.stateMachine
            if type(sm) == "table" and type(sm.session) == "table" then
                local smSession = sm.session
                stateSession.mode = smSession.mode
                stateSession.lastAction = smSession.lastAction
                stateSession.lastReason = smSession.lastReason
                if smSession.activeProfile then
                    stateSession.activeProfile = smSession.activeProfile
                end
                if type(smSession.counters) == "table" then
                    stateSession.counters = smSession.counters
                end
                if type(smSession.alerts) == "table" then
                    stateSession.alerts = smSession.alerts
                end
                stateSession.remainingBait = smSession.remainingBait
                stateSession.freeSlots = smSession.freeSlots
                stateSession.bridgeOnline = smSession.bridgeOnline
            end

            editBox:SetText("")
        end

        return enqueuedCount
    end

    -- Test 1: Empty EditBox produces no processing
    do
        local addon = Addon.new({}, {})
        local stateSession = {}
        editBox.text = ""
        editBox.getTextCallCount = 0
        editBox.setTextCallCount = 0

        local count = processInboundText(addon, editBox, stateSession)
        assertEqual(count, 0, "empty EditBox should process 0 commands")
        assertEqual(addon.stateMachine.session.mode, Contracts.Mode.IDLE, "mode should remain IDLE after empty input")
        assertEqual(editBox.getTextCallCount, 1, "GetText should be called once")
        assertEqual(editBox.setTextCallCount, 0, "SetText should NOT be called when no commands processed")
    end

    -- Test 2: Single start command is read, processed, EditBox cleared
    do
        local addon = Addon.new({}, {})
        local stateSession = {}
        editBox.text = '{"commandType":"start","profileId":"starter-pond"}'
        editBox.getTextCallCount = 0
        editBox.setTextCallCount = 0
        editBox.lastSetText = nil

        local count = processInboundText(addon, editBox, stateSession)
        assertEqual(count, 1, "start command should process 1")
        assertEqual(stateSession.mode, Contracts.Mode.SCANNING, "stateSession.mode should be SCANNING")
        assertEqual(stateSession.lastAction, Contracts.CommandType.START, "stateSession.lastAction should be start")
        assertEqual(stateSession.activeProfile, "starter-pond", "stateSession.activeProfile should sync")
        assertEqual(editBox.setTextCallCount, 1, "SetText should be called after processing")
        assertEqual(editBox.lastSetText, "", "EditBox should be cleared after processing")
    end

    -- Test 3: Multiple commands (start, pause) processed in sequence
    do
        local addon = Addon.new({}, {})
        local stateSession = {}
        editBox.text = '{"commandType":"start"}\n{"commandType":"pause"}'
        editBox.getTextCallCount = 0
        editBox.setTextCallCount = 0
        editBox.lastSetText = nil

        local count = processInboundText(addon, editBox, stateSession)
        assertEqual(count, 2, "two commands should process 2")
        assertEqual(stateSession.mode, Contracts.Mode.PAUSED, "final mode should be PAUSED after start+resume... pause")
        assertEqual(stateSession.lastAction, Contracts.CommandType.PAUSE, "lastAction should be pause")
        assertEqual(editBox.setTextCallCount, 1, "SetText should be called once after batch")
        assertEqual(editBox.lastSetText, "", "EditBox cleared after batch")
    end

    -- Test 4: Malformed JSON line is gracefully skipped
    do
        local addon = Addon.new({}, {})
        local stateSession = {}
        -- Line 2 is malformed (missing closing brace), line 3 is valid
        editBox.text = '{"commandType":"start"}\n{"commandType":"pause"\n{"commandType":"resume"}'
        editBox.getTextCallCount = 0
        editBox.setTextCallCount = 0
        editBox.lastSetText = nil

        local count = processInboundText(addon, editBox, stateSession)
        assertEqual(count, 2, "malformed JSON line should be skipped, only 2 valid commands process")
        assertEqual(stateSession.mode, Contracts.Mode.SCANNING, "final mode should be SCANNING after start,resume")
        assertEqual(stateSession.lastAction, Contracts.CommandType.RESUME, "lastAction should be resume")
        assertEqual(editBox.setTextCallCount, 1, "SetText called")
        assertEqual(editBox.lastSetText, "", "EditBox cleared after batch")
    end

    -- Test 5: Unknown command type is gracefully skipped
    do
        local addon = Addon.new({}, {})
        local stateSession = {}
        editBox.text = '{"commandType":"start"}\n{"commandType":"fly_me_to_the_moon"}'
        editBox.getTextCallCount = 0
        editBox.setTextCallCount = 0
        editBox.lastSetText = nil

        local count = processInboundText(addon, editBox, stateSession)
        assertEqual(count, 1, "unknown command type should be skipped, only valid start processes")
        assertEqual(stateSession.mode, Contracts.Mode.SCANNING, "mode should be SCANNING")
        assertEqual(stateSession.lastAction, Contracts.CommandType.START, "lastAction should be start")
    end

    -- Test 6: Whitespace-only and empty lines are ignored
    do
        local addon = Addon.new({}, {})
        local stateSession = {}
        editBox.text = '\n  \n{"commandType":"start"}\n   \n'
        editBox.getTextCallCount = 0
        editBox.setTextCallCount = 0

        local count = processInboundText(addon, editBox, stateSession)
        assertEqual(count, 1, "whitespace-only lines should be ignored")
        assertEqual(stateSession.mode, Contracts.Mode.SCANNING, "mode should be SCANNING")
        assertEqual(stateSession.lastAction, Contracts.CommandType.START, "lastAction should be start")
    end

    -- Test 7: Full state sync — counters and alerts are propagated
    do
        local addon = Addon.new({}, {})
        local stateSession = {}

        -- Start then stop to exercise state transitions
        editBox.text = '{"commandType":"start"}'
        editBox.getTextCallCount = 0
        editBox.setTextCallCount = 0
        editBox.lastSetText = nil

        local count = processInboundText(addon, editBox, stateSession)
        assertEqual(count, 1, "start command should process")
        assertEqual(type(stateSession.counters), "table", "stateSession.counters should be a table after start")

        -- Send stop
        editBox.text = '{"commandType":"stop"}'
        count = processInboundText(addon, editBox, stateSession)
        assertEqual(count, 1, "stop command should process")
        assertEqual(stateSession.mode, Contracts.Mode.IDLE, "mode should be IDLE after stop")
        assertEqual(stateSession.lastAction, Contracts.CommandType.STOP, "lastAction should be stop")
        assertEqual(editBox.lastSetText, "", "EditBox cleared after stop")
    end

    -- Test 8: sync_profile updates activeProfile through the pipeline
    do
        local addon = Addon.new({}, {})
        local stateSession = {}
        editBox.text = '{"commandType":"sync_profile","profileId":"shoreline-grind"}'
        editBox.getTextCallCount = 0
        editBox.setTextCallCount = 0

        local count = processInboundText(addon, editBox, stateSession)
        assertEqual(count, 1, "sync_profile should process")
        assertEqual(stateSession.activeProfile, "shoreline-grind", "activeProfile should sync")
        assertEqual(stateSession.lastAction, Contracts.CommandType.SYNC_PROFILE, "lastAction should be sync_profile")
    end
end

do
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    -- Real inbound command: start
    local result = JsonParser.parse('{"commandType":"start","issuedAtUtc":"2026-01-01T00:00:00Z","profileId":"starter-pond","notes":null}')
    assertEqual(result.commandType, "start", "start commandType")
    assertEqual(result.issuedAtUtc, "2026-01-01T00:00:00Z", "issuedAtUtc")
    assertEqual(result.profileId, "starter-pond", "profileId")
    assertEqual(result.notes, nil, "notes should be nil")

    -- Real inbound command: sync_profile
    result = JsonParser.parse('{"commandType":"sync_profile","profileId":"shoreline-grind"}')
    assertEqual(result.commandType, "sync_profile", "sync_profile commandType")
    assertEqual(result.profileId, "shoreline-grind", "sync_profile profileId")

    -- Real inbound command: request_snapshot
    result = JsonParser.parse('{"commandType":"request_snapshot","notes":"Manual test"}')
    assertEqual(result.commandType, "request_snapshot", "request_snapshot commandType")
    assertEqual(result.notes, "Manual test", "request_snapshot notes")
end

-- ── Full Python → Lua → Python round-trip via simulated clipboard ────
-- This test simulates the entire clipboard bridge cycle:
--   1. Python writes a command JSON to the bridge EditBox
--   2. Lua reads it, processes via consumeInboundCommands pipeline
--   3. Lua builds outbound session-status, serializes to JSON, writes back
--   4. Python reads the EditBox and parses the JSON

do
    local Addon = require("AutoFish.AutoFishAddon")
    local CommandNormalizer = require("AutoFish.Bridge.CommandNormalizer")
    local Contracts = require("AutoFish.Bridge.Contracts")
    local JsonParser = require("AutoFish.Bridge.JsonParser")
    local SnapshotBuilder = require("AutoFish.Core.SnapshotBuilder")
    local EnvelopeBuilder = require("AutoFish.Bridge.EnvelopeBuilder")

    -- tableToJson: mirrors Main.lua's local function for serializing outbound payloads
    local function tableToJson(value, depth, visited)
        depth = depth or 0
        if depth > 24 then return "null" end
        local t = type(value)
        if t == "nil" then
            return "null"
        elseif t == "boolean" then
            return tostring(value)
        elseif t == "number" then
            if value ~= value or value == math.huge then return "null" end
            return tostring(value)
        elseif t == "string" then
            local escaped = string.gsub(value, '["\\\n\r\t]', {
                ['"'] = '\\"',
                ['\\'] = '\\\\',
                ['\n'] = '\\n',
                ['\r'] = '\\r',
                ['\t'] = '\\t',
            })
            return '"' .. escaped .. '"'
        elseif t ~= "table" then
            return '"' .. tostring(value) .. '"'
        end
        visited = visited or {}
        if visited[value] then return "null" end
        visited[value] = true

        local maxIdx, count = 0, 0
        local isArray = true
        for k, _ in pairs(value) do
            count = count + 1
            if type(k) == "number" and k >= 1 and math.floor(k) == k then
                if k > maxIdx then maxIdx = k end
            else
                isArray = false
            end
        end

        if isArray and count > 0 and maxIdx == count then
            local elems = {}
            for i = 1, count do
                elems[i] = tableToJson(value[i], depth + 1, visited)
            end
            return "[" .. table.concat(elems, ",") .. "]"
        end

        local parts, keys = {}, {}
        for k, _ in pairs(value) do keys[#keys + 1] = k end
        table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
        for _, k in ipairs(keys) do
            local v = value[k]
            if v ~= nil then
                parts[#parts + 1] = tableToJson(k, depth + 1, visited) .. ":" .. tableToJson(v, depth + 1, visited)
            end
        end
        if #parts == 0 then return "{}" end
        return "{" .. table.concat(parts, ",") .. "}"
    end

    -- Ensure tableToJson handles all the types in a session-status envelope
    do
        local json = tableToJson(nil, 0, {})
        assertEqual(json, "null", "tableToJson(nil) should produce null")

        json = tableToJson(true, 0, {})
        assertEqual(json, "true", "tableToJson(true) should produce true")

        json = tableToJson(false, 0, {})
        assertEqual(json, "false", "tableToJson(false) should produce false")

        json = tableToJson(42, 0, {})
        assertEqual(json, "42", "tableToJson(42) should produce 42")

        json = tableToJson("hello", 0, {})
        assertEqual(json, '"hello"', "tableToJson(hello) should produce a quoted string")

        json = tableToJson({a = 1, b = "two"}, 0, {})
        -- Keys sorted alphabetically: a, b
        assertEqual(json, '{"a":1,"b":"two"}', "tableToJson({a=1,b=two}) should produce sorted kv pairs")

        json = tableToJson({}, 0, {})
        assertEqual(json, "{}", "tableToJson({}) should produce empty object")

        json = tableToJson({1, 2, 3}, 0, {})
        assertEqual(json, "[1,2,3]", "tableToJson(array) should produce a JSON array")
    end

    -- Mock EditBox
    local editBox = {
        text = "",
        getTextCallCount = 0,
        setTextCallCount = 0,
        lastSetText = nil,
        GetText = function(self)
            self.getTextCallCount = self.getTextCallCount + 1
            return self.text
        end,
        SetText = function(self, newText)
            self.setTextCallCount = self.setTextCallCount + 1
            self.lastSetText = newText
        end,
    }

    -- Helper: simulate consumeInboundCommands processing loop
    local function processInboundText(addon, editBox, stateSession)
        local text = editBox:GetText()
        if type(text) ~= "string" or text == "" then
            return 0
        end

        local enqueuedCount = 0
        for line in string.gmatch(text, "[^\n]+") do
            local trimmed = string.match(line, "^%s*(.-)%s*$")
            if trimmed and trimmed ~= "" then
                local okParse, parsed = pcall(JsonParser.parse, trimmed)
                if okParse and type(parsed) == "table" then
                    local command, reason = CommandNormalizer.normalize(parsed)
                    if command then
                        addon.bus:enqueueInbound(command)
                        enqueuedCount = enqueuedCount + 1
                    end
                end
            end
        end

        if enqueuedCount > 0 then
            addon:handleInboundCommands()

            local sm = addon.stateMachine
            if type(sm) == "table" and type(sm.session) == "table" then
                local smSession = sm.session
                stateSession.mode = smSession.mode
                stateSession.lastAction = smSession.lastAction
                stateSession.lastReason = smSession.lastReason
                if smSession.activeProfile then
                    stateSession.activeProfile = smSession.activeProfile
                end
                if type(smSession.counters) == "table" then
                    stateSession.counters = smSession.counters
                end
                if type(smSession.alerts) == "table" then
                    stateSession.alerts = smSession.alerts
                end
                stateSession.remainingBait = smSession.remainingBait
                stateSession.freeSlots = smSession.freeSlots
                stateSession.bridgeOnline = smSession.bridgeOnline
            end

            editBox:SetText("")
        end

        return enqueuedCount
    end

    -- Helper: simulate flushBridgeOutbound outbound flow
    -- Builds snapshot, wraps in session_status envelope, enqueues, drains, serializes, writes to EditBox
    local function simulateOutboundFlush(addon, stateSession, editBox)
        local session = stateSession or {}
        local characterName = "player"
        local observation = {
            inGame = true,
            nearWater = true,
            inCombat = false,
            inventoryFull = false,
            bridgeOnline = addon.stateMachine and addon.stateMachine.session.bridgeOnline or false,
        }

        local ok, snapshot = pcall(SnapshotBuilder.build, session, characterName, observation)
        if not ok or type(snapshot) ~= "table" then
            return nil, "snapshot build failed: " .. tostring(snapshot)
        end

        local envelope, err = EnvelopeBuilder.buildSessionStatus(snapshot)
        if not envelope then
            return nil, "envelope build failed: " .. tostring(err)
        end

        -- Enqueue outbound via addon's bus (same path as onObservation)
        addon.bus:enqueueOutbound(envelope)

        -- Drain outbound messages
        local drained = addon.bus:drainOutbound()
        if type(drained) ~= "table" or #drained == 0 then
            return nil, "no outbound messages to drain"
        end

        -- Serialize each payload to JSON (same as flushBridgeOutbound's tableToJson step)
        local lines = {}
        for _, payload in ipairs(drained) do
            local ok, line = pcall(tableToJson, payload, 0, {})
            if ok and type(line) == "string" then
                lines[#lines + 1] = line
            end
        end

        if #lines == 0 then
            return nil, "serialization produced no lines"
        end

        local jsonText = table.concat(lines, "\n")
        editBox:SetText(jsonText)

        return {
            envelopeCount = #drained,
            jsonText = jsonText,
        }, nil
    end

    -- Test 1: Basic start command round trip
    do
        local addon = Addon.new({}, {})
        local stateSession = {}

        -- Step 1: Python writes a start command to the bridge EditBox
        editBox.text = '{"commandType":"start","profileId":"starter-pond"}'
        editBox.getTextCallCount = 0
        editBox.setTextCallCount = 0
        editBox.lastSetText = nil

        -- Step 2: Lua reads and processes (consumeInboundCommands simulation)
        local count = processInboundText(addon, editBox, stateSession)
        assertEqual(count, 1, "round-trip: start command should process 1")
        assertEqual(stateSession.mode, Contracts.Mode.SCANNING, "round-trip: mode should be SCANNING after start")
        assertEqual(stateSession.lastAction, Contracts.CommandType.START, "round-trip: lastAction should be start")
        assertEqual(stateSession.activeProfile, "starter-pond", "round-trip: activeProfile should be starter-pond")

        -- Step 3: Lua builds outbound session-status and writes to EditBox
        local result, err = simulateOutboundFlush(addon, stateSession, editBox)
        assertEqual(type(result), "table", "round-trip: outbound flush should succeed, got error: " .. tostring(err))
        assertEqual(type(editBox.lastSetText), "string", "round-trip: EditBox should contain JSON text")
        assertEqual(#editBox.lastSetText > 0, true, "round-trip: JSON text should not be empty")

        -- Step 4: Python reads the EditBox and parses the JSON back
        local parsed, parseErr = JsonParser.parse(editBox.lastSetText)
        assertEqual(type(parsed), "table", "round-trip: Python should parse the outbound JSON, got error: " .. tostring(parseErr))

        -- Verify envelope structure matches what Python helper expects
        assertEqual(parsed.messageType, Contracts.MessageType.SESSION_STATUS, "round-trip: messageType should be session_status")
        assertEqual(parsed.contractVersion, "1.0.0", "round-trip: contractVersion should be 1.0.0")
        assertEqual(type(parsed.issuedAtUtc), "string", "round-trip: issuedAtUtc should be a string")
        assertEqual(type(parsed.payload), "table", "round-trip: envelope should have payload")

        -- Verify payload reflects the state change from the inbound command
        assertEqual(parsed.payload.mode, Contracts.Mode.SCANNING, "round-trip: payload mode should be scanning")
        assertEqual(parsed.payload.lastAction, Contracts.CommandType.START, "round-trip: payload lastAction should be start")
        assertEqual(parsed.payload.activeProfile, "starter-pond", "round-trip: payload activeProfile should be starter-pond")
        assertEqual(type(parsed.payload.counters), "table", "round-trip: payload should have counters")
        assertEqual(type(parsed.payload.updatedAtUtc), "string", "round-trip: payload should have updatedAtUtc")
        assertEqual(type(parsed.payload.alerts), "table", "round-trip: payload should have alerts array")
    end

    -- Test 2: Pause command round trip (verify state transition)
    do
        local addon = Addon.new({}, {})
        local stateSession = {}

        editBox.text = '{"commandType":"start"}'
        editBox.getTextCallCount = 0
        editBox.setTextCallCount = 0
        editBox.lastSetText = nil

        processInboundText(addon, editBox, stateSession)

        -- Now send pause in a second batch
        editBox.text = '{"commandType":"pause"}'
        processInboundText(addon, editBox, stateSession)

        -- Outbound should reflect PAUSED state
        local result, err = simulateOutboundFlush(addon, stateSession, editBox)
        assertEqual(type(result), "table", "round-trip pause: outbound flush should succeed")

        local parsed, _ = JsonParser.parse(editBox.lastSetText)
        assertEqual(type(parsed), "table", "round-trip pause: should parse outbound JSON")
        assertEqual(parsed.payload.mode, Contracts.Mode.PAUSED, "round-trip pause: payload mode should be paused")
        assertEqual(parsed.payload.lastAction, Contracts.CommandType.PAUSE, "round-trip pause: payload lastAction should be pause")
        assertEqual(parsed.payload.inGame, true, "round-trip pause: payload inGame should default to true")
        assertEqual(parsed.payload.inCombat, false, "round-trip pause: payload inCombat should default to false")
    end

    -- Test 3: sync_profile round trip
    do
        local addon = Addon.new({}, {})
        local stateSession = {}

        editBox.text = '{"commandType":"sync_profile","profileId":"shoreline-grind"}'
        editBox.getTextCallCount = 0
        editBox.setTextCallCount = 0
        editBox.lastSetText = nil

        local count = processInboundText(addon, editBox, stateSession)
        assertEqual(count, 1, "round-trip sync_profile: should process 1")
        assertEqual(stateSession.activeProfile, "shoreline-grind", "round-trip sync_profile: activeProfile should be shoreline-grind")

        local result, err = simulateOutboundFlush(addon, stateSession, editBox)
        assertEqual(type(result), "table", "round-trip sync_profile: outbound flush should succeed")

        local parsed, _ = JsonParser.parse(editBox.lastSetText)
        assertEqual(type(parsed), "table", "round-trip sync_profile: should parse outbound JSON")
        assertEqual(parsed.payload.activeProfile, "shoreline-grind", "round-trip sync_profile: payload activeProfile should be shoreline-grind")
        assertEqual(parsed.payload.lastAction, Contracts.CommandType.SYNC_PROFILE, "round-trip sync_profile: payload lastAction should be sync_profile")
    end

    -- Test 4: Stop command — verify the round trip to IDLE state
    do
        local addon = Addon.new({}, {})
        local stateSession = {}

        -- Start, then stop
        editBox.text = '{"commandType":"start"}'
        editBox.getTextCallCount = 0
        editBox.setTextCallCount = 0
        editBox.lastSetText = nil
        processInboundText(addon, editBox, stateSession)

        editBox.text = '{"commandType":"stop"}'
        processInboundText(addon, editBox, stateSession)

        local result, err = simulateOutboundFlush(addon, stateSession, editBox)
        assertEqual(type(result), "table", "round-trip stop: outbound flush should succeed")

        local parsed, _ = JsonParser.parse(editBox.lastSetText)
        assertEqual(type(parsed), "table", "round-trip stop: should parse outbound JSON")
        assertEqual(parsed.payload.mode, Contracts.Mode.IDLE, "round-trip stop: payload mode should be idle after stop")
        assertEqual(parsed.payload.lastAction, Contracts.CommandType.STOP, "round-trip stop: payload lastAction should be stop")

        -- Verify counters are present in the payload (they should be initialized even without casting)
        local counters = parsed.payload.counters
        assertEqual(type(counters), "table", "round-trip stop: counters should be a table")
        assertEqual(counters.casts, 0, "round-trip stop: casts should be 0")
        assertEqual(counters.hooksets, 0, "round-trip stop: hooksets should be 0")
        assertEqual(counters.catches, 0, "round-trip stop: catches should be 0")
        assertEqual(counters.recoveries, 0, "round-trip stop: recoveries should be 0")

        -- Verify the serialized JSON is valid (can be parsed twice)
        local reparsed, _ = JsonParser.parse(editBox.lastSetText)
        assertEqual(reparsed.payload.mode, Contracts.Mode.IDLE, "round-trip stop: re-parse should produce same mode")
        assertEqual(reparsed.payload.counters.casts, 0, "round-trip stop: re-parse should produce same counters")
    end

    -- Test 5: Serialized JSON should contain all expected envelope fields
    do
        local addon = Addon.new({}, {})
        local stateSession = {}

        editBox.text = '{"commandType":"start","profileId":"starter-pond"}'
        editBox.getTextCallCount = 0
        editBox.setTextCallCount = 0
        editBox.lastSetText = nil
        processInboundText(addon, editBox, stateSession)

        local result, err = simulateOutboundFlush(addon, stateSession, editBox)
        assertEqual(type(result), "table", "round-trip envelope fields: outbound flush should succeed")

        local parsed, _ = JsonParser.parse(editBox.lastSetText)
        assertEqual(type(parsed), "table", "round-trip envelope fields: should parse")

        -- Verify the JSON round-trips correctly through tableToJson -> JsonParser.parse
        local text = editBox.lastSetText
        assertEqual(type(string.match(text, '"messageType":"session_status"')), "string",
            "round-trip: serialized JSON should contain messageType field")
        assertEqual(type(string.match(text, '"contractVersion":"1%.0%.0"')), "string",
            "round-trip: serialized JSON should contain contractVersion")
        assertEqual(type(string.match(text, '"issuedAtUtc":"')), "string",
            "round-trip: serialized JSON should contain issuedAtUtc")
        assertEqual(type(string.match(text, '"payload":{')), "string",
            "round-trip: serialized JSON should contain payload object")
        assertEqual(type(string.match(text, '"mode":"scanning"')), "string",
            "round-trip: serialized JSON should contain mode in payload")
        assertEqual(type(string.match(text, '"updatedAtUtc":"')), "string",
            "round-trip: serialized JSON should contain updatedAtUtc in payload")
    end
end

-- ── Inbound command end-to-end flow tests ──────────────────────────

do
    local Addon = require("AutoFish.AutoFishAddon")
    local CommandNormalizer = require("AutoFish.Bridge.CommandNormalizer")
    local Contracts = require("AutoFish.Bridge.Contracts")
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    local addon = Addon.new({}, {})

    -- Parse a start command and feed it through the full pipeline
    local parsed, err = JsonParser.parse('{"commandType":"start","profileId":"starter-pond"}')
    assertEqual(type(parsed), "table", "start JSON should parse")

    local command, reason = CommandNormalizer.normalize(parsed)
    assertEqual(type(command), "table", "start command should normalize")
    assertEqual(command.commandType, "start", "normalized commandType")
    assertEqual(command.profileId, "starter-pond", "normalized profileId")

    -- Enqueue through the addon's bus (same path consumeInboundCommands uses)
    local enqueued = addon.bus:enqueueInbound(command)
    assertEqual(enqueued, true, "start command should enqueue")

    -- Process via handleInboundCommands (same path consumeInboundCommands uses)
    local processed = addon:handleInboundCommands()
    assertEqual(processed, 1, "should process 1 command")

    -- Verify state machine applied the command
    assertEqual(addon.stateMachine.session.mode, Contracts.Mode.SCANNING, "start command should set mode to SCANNING")
    assertEqual(addon.stateMachine.session.lastAction, Contracts.CommandType.START, "lastAction should be start")
end

do
    local Addon = require("AutoFish.AutoFishAddon")
    local CommandNormalizer = require("AutoFish.Bridge.CommandNormalizer")
    local Contracts = require("AutoFish.Bridge.Contracts")
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    local addon = Addon.new({}, {})

    -- Test pause/resume cycle
    local function sendCommand(jsonStr)
        local parsed, _ = JsonParser.parse(jsonStr)
        local command, _ = CommandNormalizer.normalize(parsed)
        addon.bus:enqueueInbound(command)
        return addon:handleInboundCommands()
    end

    -- Start
    sendCommand('{"commandType":"start"}')
    assertEqual(addon.stateMachine.session.mode, Contracts.Mode.SCANNING, "mode should be SCANNING after start")

    -- Pause
    sendCommand('{"commandType":"pause"}')
    assertEqual(addon.stateMachine.session.mode, Contracts.Mode.PAUSED, "mode should be PAUSED after pause")
    assertEqual(addon.stateMachine.session.lastAction, Contracts.CommandType.PAUSE, "lastAction should be pause")

    -- Resume
    sendCommand('{"commandType":"resume"}')
    assertEqual(addon.stateMachine.session.mode, Contracts.Mode.SCANNING, "mode should be SCANNING after resume")
    assertEqual(addon.stateMachine.session.lastAction, Contracts.CommandType.RESUME, "lastAction should be resume")

    -- Stop
    sendCommand('{"commandType":"stop"}')
    assertEqual(addon.stateMachine.session.mode, Contracts.Mode.IDLE, "mode should be IDLE after stop")
    assertEqual(addon.stateMachine.session.lastAction, Contracts.CommandType.STOP, "lastAction should be stop")
end

do
    local Addon = require("AutoFish.AutoFishAddon")
    local CommandNormalizer = require("AutoFish.Bridge.CommandNormalizer")
    local Contracts = require("AutoFish.Bridge.Contracts")
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    local addon = Addon.new({}, {})

    -- sync_profile command should update the active profile
    local function sendCommand(jsonStr)
        local parsed, _ = JsonParser.parse(jsonStr)
        local command, _ = CommandNormalizer.normalize(parsed)
        addon.bus:enqueueInbound(command)
        return addon:handleInboundCommands()
    end

    sendCommand('{"commandType":"sync_profile","profileId":"shoreline-grind"}')
    assertEqual(addon.stateMachine.session.activeProfile, "shoreline-grind", "sync_profile should update activeProfile")
    assertEqual(addon.stateMachine.session.lastAction, Contracts.CommandType.SYNC_PROFILE, "lastAction should be sync_profile")
end

do
    local Addon = require("AutoFish.AutoFishAddon")
    local CommandNormalizer = require("AutoFish.Bridge.CommandNormalizer")
    local Contracts = require("AutoFish.Bridge.Contracts")
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    local addon = Addon.new({}, {})

    -- request_snapshot command should update lastAction without changing mode
    local initialMode = addon.stateMachine.session.mode

    local parsed, _ = JsonParser.parse('{"commandType":"request_snapshot","notes":"operator requested"}')
    local command, _ = CommandNormalizer.normalize(parsed)
    addon.bus:enqueueInbound(command)
    local processed = addon:handleInboundCommands()

    assertEqual(processed, 1, "request_snapshot should process")
    assertEqual(addon.stateMachine.session.lastAction, Contracts.CommandType.REQUEST_SNAPSHOT, "lastAction should be request_snapshot")
    assertEqual(addon.stateMachine.session.mode, initialMode, "request_snapshot should not change mode")
end

do
    local Addon = require("AutoFish.AutoFishAddon")
    local CommandNormalizer = require("AutoFish.Bridge.CommandNormalizer")
    local Contracts = require("AutoFish.Bridge.Contracts")
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    local addon = Addon.new({}, {})

    -- Unknown command types should be rejected at normalization
    local parsed, _ = JsonParser.parse('{"commandType":"unknown_crap"}')
    local command, reason = CommandNormalizer.normalize(parsed)
    assertEqual(command, nil, "unknown commandType should return nil")
    assertEqual(reason, "commandType is not recognized", "unknown commandType error message")
end

do
    local Addon = require("AutoFish.AutoFishAddon")
    local CommandNormalizer = require("AutoFish.Bridge.CommandNormalizer")
    local Contracts = require("AutoFish.Bridge.Contracts")
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    local addon = Addon.new({}, {})

    -- Malformed JSON should be safely ignored (pcall guards in consumeInboundCommands)
    local function sendCommand(jsonStr)
        local parsed, err = JsonParser.parse(jsonStr)
        if parsed == nil then
            return 0  -- consumedInboundCommands skips this line
        end
        local command, _ = CommandNormalizer.normalize(parsed)
        if command then
            addon.bus:enqueueInbound(command)
            return addon:handleInboundCommands()
        end
        return 0
    end

    local processed = sendCommand('{"commandType": "start"')  -- unterminated
    assertEqual(processed, 0, "malformed JSON should not be processed")
    assertEqual(addon.stateMachine.session.mode, Contracts.Mode.IDLE, "mode should remain IDLE after malformed JSON")
end

do
    local Addon = require("AutoFish.AutoFishAddon")
    local CommandNormalizer = require("AutoFish.Bridge.CommandNormalizer")
    local Contracts = require("AutoFish.Bridge.Contracts")
    local JsonParser = require("AutoFish.Bridge.JsonParser")

    local addon = Addon.new({}, {})

    -- Null notes field should pass through normalization
    local parsed, _ = JsonParser.parse('{"commandType":"start","profileId":"starter-pond","notes":null,"issuedAtUtc":"2026-01-01T00:00:00Z"}')
    local command, _ = CommandNormalizer.normalize(parsed)
    assertEqual(command.notes, nil, "null notes should remain nil after normalization")
    assertEqual(command.commandType, "start", "commandType preserved when notes is null")
    assertEqual(command.profileId, "starter-pond", "profileId preserved when notes is null")
    assertEqual(command.issuedAtUtc, "2026-01-01T00:00:00Z", "issuedAtUtc preserved when notes is null")

    addon.bus:enqueueInbound(command)
    local processed = addon:handleInboundCommands()
    assertEqual(processed, 1, "start command with null notes should process")
    assertEqual(addon.stateMachine.session.mode, Contracts.Mode.SCANNING, "mode should be SCANNING after start with null notes")
end
