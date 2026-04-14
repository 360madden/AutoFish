local Contracts = require("AutoFish.Bridge.Contracts")

local Guardrails = {}

function Guardrails.evaluate(observation, config)
    if not observation.inGame then
        return { action = "pause", mode = Contracts.Mode.PAUSED, reason = "game signal missing" }
    end

    if observation.inCombat and config.pauseOnCombat then
        return { action = "pause", mode = Contracts.Mode.PAUSED, reason = "combat detected" }
    end

    if observation.inventoryFull then
        return { action = "maintenance", mode = Contracts.Mode.MAINTENANCE, reason = "inventory full" }
    end

    if not observation.baitAvailable then
        return { action = "rebait", mode = Contracts.Mode.MAINTENANCE, reason = "bait depleted" }
    end

    if not observation.nearWater and config.recoverOnDrift then
        return { action = "recover_position", mode = Contracts.Mode.RECOVERING, reason = "drifted away from fishing position" }
    end

    return nil
end

return Guardrails
