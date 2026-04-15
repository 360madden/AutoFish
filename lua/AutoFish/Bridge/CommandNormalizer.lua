local Contracts = require("AutoFish.Bridge.Contracts")

local CommandNormalizer = {}

local knownCommands = {
    [Contracts.CommandType.START] = true,
    [Contracts.CommandType.PAUSE] = true,
    [Contracts.CommandType.RESUME] = true,
    [Contracts.CommandType.STOP] = true,
    [Contracts.CommandType.SYNC_PROFILE] = true,
    [Contracts.CommandType.REQUEST_SNAPSHOT] = true,
    [Contracts.CommandType.ACK] = true,
}

function CommandNormalizer.normalize(command)
    if type(command) ~= "table" then
        return nil, "command payload must be a table"
    end

    local commandType = command.commandType
    if type(commandType) ~= "string" or commandType == "" then
        return nil, "commandType must be a non-empty string"
    end

    if not knownCommands[commandType] then
        return nil, "commandType is not recognized"
    end

    local profileId = type(command.profileId) == "string" and command.profileId or nil
    if profileId == "" then
        profileId = nil
    end

    return {
        commandType = commandType,
        issuedAtUtc = type(command.issuedAtUtc) == "string" and command.issuedAtUtc or os.date("!%Y-%m-%dT%H:%M:%SZ"),
        profileId = profileId,
        notes = type(command.notes) == "string" and command.notes or nil,
    }, nil
end

return CommandNormalizer
