local Contracts = require("AutoFish.Bridge.Contracts")

local Controller = {}

local intentMap = {
    start = Contracts.CommandType.START,
    pause = Contracts.CommandType.PAUSE,
    resume = Contracts.CommandType.RESUME,
    stop = Contracts.CommandType.STOP,
    sync_profile = Contracts.CommandType.SYNC_PROFILE,
    request_snapshot = Contracts.CommandType.REQUEST_SNAPSHOT,
}

function Controller.intentToCommand(intent, profileId, notes)
    local commandType = intentMap[intent]
    if not commandType then
        return nil
    end

    return {
        commandType = commandType,
        issuedAtUtc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
        profileId = profileId,
        notes = notes,
    }
end

return Controller
