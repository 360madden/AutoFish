local Contracts = require("AutoFish.Bridge.Contracts")

local EnvelopeBuilder = {}

local knownMessageTypes = {
    [Contracts.MessageType.ACK] = true,
    [Contracts.MessageType.SESSION_STATUS] = true,
    [Contracts.MessageType.COMMAND] = true,
}

function EnvelopeBuilder.build(messageType, payload)
    if type(messageType) ~= "string" or not knownMessageTypes[messageType] then
        return nil, "messageType is not recognized"
    end

    if type(payload) ~= "table" then
        return nil, "payload must be a table"
    end

    return {
        messageType = messageType,
        contractVersion = Contracts.ContractVersion,
        issuedAtUtc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
        payload = payload,
    }, nil
end

function EnvelopeBuilder.buildAck(decision)
    decision = type(decision) == "table" and decision or {}

    return EnvelopeBuilder.build(Contracts.MessageType.ACK, {
        action = type(decision.action) == "string" and decision.action or "pause",
        reason = type(decision.reason) == "string" and decision.reason or "acknowledgement generated without a concrete decision",
    })
end

function EnvelopeBuilder.buildSessionStatus(snapshot)
    return EnvelopeBuilder.build(Contracts.MessageType.SESSION_STATUS, snapshot)
end

return EnvelopeBuilder
