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
        return nil
    end

    local commandType = command.commandType
    if type(commandType) ~= "string" or not knownCommands[commandType] then
        return nil
    end

    return {
        commandType = commandType,
        issuedAtUtc = type(command.issuedAtUtc) == "string" and command.issuedAtUtc or os.date("!%Y-%m-%dT%H:%M:%SZ"),
        profileId = type(command.profileId) == "string" and command.profileId or nil,
        notes = type(command.notes) == "string" and command.notes or nil,
    }
end

return CommandNormalizer
