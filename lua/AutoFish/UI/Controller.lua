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
    if type(intent) ~= "string" or intent == "" then
        return nil, "intent must be a non-empty string"
    end

    local commandType = intentMap[intent]
    if not commandType then
        return nil, "intent is not recognized"
    end

    local normalizedProfileId = type(profileId) == "string" and profileId ~= "" and profileId or nil
    local normalizedNotes = type(notes) == "string" and notes ~= "" and notes or nil

    return {
        commandType = commandType,
        issuedAtUtc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
        profileId = normalizedProfileId,
        notes = normalizedNotes,
    }, nil
end

return Controller
