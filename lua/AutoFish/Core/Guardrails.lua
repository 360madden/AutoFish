local Contracts = require("AutoFish.Bridge.Contracts")
local GuardrailRules = require("AutoFish.Core.GuardrailRules")

local Guardrails = {}

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

local function logIfAvailable(logger, level, message, context)
    if not logger or type(logger[level]) ~= "function" then
        return
    end

    logger[level](logger, message, normalizeContext(context))
end

function Guardrails.evaluate(observation, config, session, logger)
    session = session or {}
    local context = {
        observation = observation,
        config = config,
        session = session,
    }

    for _, rule in ipairs(GuardrailRules.getAll()) do
        local decision = rule.evaluate(context)
        if decision then
            decision.ruleId = decision.ruleId or rule.id
            logIfAvailable(logger, "warn", "Guardrail triggered.", {
                ruleId = decision.ruleId,
                action = decision.action,
                mode = decision.mode,
                reason = decision.reason,
            })
            return decision
        end
    end

    return nil
end

return Guardrails
