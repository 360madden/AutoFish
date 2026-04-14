local Defaults = {}

function Defaults.normalize(config)
    config = config or {}
    return {
        baitCapacity = config.baitCapacity or 20,
        inventoryCapacity = config.inventoryCapacity or 12,
        rebaitAtOrBelow = config.rebaitAtOrBelow or 5,
        maintenanceAtFreeSlotsOrBelow = config.maintenanceAtFreeSlotsOrBelow or 2,
        pauseOnCombat = config.pauseOnCombat ~= false,
        recoverOnDrift = config.recoverOnDrift ~= false,
    }
end

return Defaults
