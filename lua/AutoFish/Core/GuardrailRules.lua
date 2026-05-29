local Contracts = AutoFish.Bridge.Contracts
local Observation = AutoFish.Core.Observation

local GuardrailRules = {}

local rules = {
    {
        id = "bridge_loss_pause",
        evaluate = function(context)
            if context.session.bridgeWasOnline and not context.session.bridgeOnline and context.config.pauseOnBridgeLoss then
                return {
                    action = "pause",
                    mode = Contracts.Mode.PAUSED,
                    reason = "bridge connection lost",
                }
            end

            return nil
        end,
    },
    {
        id = "missing_game_signal_pause",
        evaluate = function(context)
            if not Observation.boolean(context.observation, "inGame", false) then
                return {
                    action = "pause",
                    mode = Contracts.Mode.PAUSED,
                    reason = "game signal missing",
                }
            end

            return nil
        end,
    },
    {
        id = "combat_pause",
        evaluate = function(context)
            if Observation.boolean(context.observation, "inCombat", false) and context.config.pauseOnCombat then
                return {
                    action = "pause",
                    mode = Contracts.Mode.PAUSED,
                    reason = "combat detected",
                }
            end

            return nil
        end,
    },
    {
        id = "inventory_maintenance",
        evaluate = function(context)
            if Observation.boolean(context.observation, "inventoryFull", false) then
                return {
                    action = "maintenance",
                    mode = Contracts.Mode.MAINTENANCE,
                    reason = "inventory full",
                }
            end

            return nil
        end,
    },
    {
        id = "bait_rebait",
        evaluate = function(context)
            if not Observation.boolean(context.observation, "baitAvailable", false) then
                return {
                    action = "rebait",
                    mode = Contracts.Mode.MAINTENANCE,
                    reason = "bait depleted",
                }
            end

            return nil
        end,
    },
    {
        id = "drift_recovery_or_pause",
        evaluate = function(context)
            if Observation.boolean(context.observation, "nearWater", false) or not context.config.recoverOnDrift then
                return nil
            end

            if context.session.recoveryAttempts >= context.config.maxRecoveryAttempts then
                return {
                    action = "pause",
                    mode = Contracts.Mode.PAUSED,
                    reason = "drift recovery limit reached",
                }
            end

            return {
                action = "recover_position",
                mode = Contracts.Mode.RECOVERING,
                reason = "drifted away from fishing position",
            }
        end,
    },
}

function GuardrailRules.getAll()
    return rules
end

AutoFish = AutoFish or {}
AutoFish.Core = AutoFish.Core or {}
AutoFish.Core.GuardrailRules = GuardrailRules
if require ~= nil then return GuardrailRules end
