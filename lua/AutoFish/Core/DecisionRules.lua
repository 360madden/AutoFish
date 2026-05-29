local Contracts = AutoFish.Bridge.Contracts

local DecisionRules = {}

local rules = {
    {
        id = "loot_reaction_window",
        evaluate = function(context)
            if not context.lootReady then
                return nil
            end

            local lootDelayMs = math.min(context.reactionDelayMs, context.config.lootTimeoutMs)
            if context.lootReadyForMs < lootDelayMs then
                return {
                    action = "wait",
                    mode = Contracts.Mode.WAITING_BITE,
                    reason = "waiting for loot reaction window",
                }
            end

            return {
                action = "loot",
                mode = Contracts.Mode.LOOTING,
                reason = "loot ready",
            }
        end,
    },
    {
        id = "bite_reaction_window",
        evaluate = function(context)
            if not context.biteDetected then
                return nil
            end

            local biteDelayMs = math.min(context.reactionDelayMs, context.config.biteTimeoutMs)
            if context.biteDetectedForMs < biteDelayMs then
                return {
                    action = "wait",
                    mode = Contracts.Mode.WAITING_BITE,
                    reason = "waiting for bite reaction window",
                }
            end

            return {
                action = "set_hook",
                mode = Contracts.Mode.HOOKING,
                reason = "bite detected",
            }
        end,
    },
    {
        id = "recycle_stale_cast",
        evaluate = function(context)
            if context.lineCast and context.lineCastForMs >= context.config.biteTimeoutMs and context.canCast then
                return {
                    action = "cast_line",
                    mode = Contracts.Mode.CASTING,
                    reason = "bite timeout exceeded; recycling cast",
                }
            end

            return nil
        end,
    },
    {
        id = "cast_when_ready",
        evaluate = function(context)
            if not context.lineCast and context.canCast and context.nearWater then
                return {
                    action = "cast_line",
                    mode = Contracts.Mode.CASTING,
                    reason = "ready to cast",
                }
            end

            return nil
        end,
    },
    {
        id = "wait_for_event",
        evaluate = function()
            return {
                action = "wait",
                mode = Contracts.Mode.WAITING_BITE,
                reason = "waiting for bite or loot event",
            }
        end,
    },
}

function DecisionRules.evaluate(context)
    for _, rule in ipairs(rules) do
        local decision = rule.evaluate(context)
        if decision then
            decision.ruleId = decision.ruleId or rule.id
            return decision
        end
    end

    return nil
end

function DecisionRules.getAll()
    return rules
end

AutoFish = AutoFish or {}
AutoFish.Core = AutoFish.Core or {}
AutoFish.Core.DecisionRules = DecisionRules
if require ~= nil then return DecisionRules end
