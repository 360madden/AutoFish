local MessageBus = {}
MessageBus.__index = MessageBus

function MessageBus.new()
    return setmetatable({
        outbound = {},
        inbound = {},
        bridgeOnline = false,
        lastHeartbeatUtc = nil,
    }, MessageBus)
end

function MessageBus:setBridgeOnline(isOnline, heartbeatUtc)
    self.bridgeOnline = isOnline == true
    self.lastHeartbeatUtc = heartbeatUtc or self.lastHeartbeatUtc
end

function MessageBus:enqueueOutbound(payload)
    table.insert(self.outbound, payload)
end

function MessageBus:enqueueInbound(payload)
    table.insert(self.inbound, payload)
end

function MessageBus:drainOutbound()
    local drained = self.outbound
    self.outbound = {}
    return drained
end

function MessageBus:drainInbound()
    local drained = self.inbound
    self.inbound = {}
    return drained
end

function MessageBus:getStatus()
    return {
        bridgeOnline = self.bridgeOnline,
        lastHeartbeatUtc = self.lastHeartbeatUtc,
        outboundQueued = #self.outbound,
        inboundQueued = #self.inbound,
    }
end

return MessageBus
