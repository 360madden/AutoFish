local Contracts = require("AutoFish.Bridge.Contracts")

local EnvelopeBuilder = {}

function EnvelopeBuilder.build(messageType, payload)
    return {
        messageType = messageType,
        contractVersion = Contracts.ContractVersion,
        issuedAtUtc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
        payload = payload,
    }
end

function EnvelopeBuilder.buildAck(decision)
    return EnvelopeBuilder.build(Contracts.MessageType.ACK, {
        action = decision.action,
        reason = decision.reason,
    })
end

function EnvelopeBuilder.buildSessionStatus(snapshot)
    return EnvelopeBuilder.build(Contracts.MessageType.SESSION_STATUS, snapshot)
end

return EnvelopeBuilder
