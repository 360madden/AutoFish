local MessageBus = {}
MessageBus.__index = MessageBus

local function getQueue(self, queueName)
    local queue = self[queueName]
    if type(queue) == "table" then
        return queue
    end

    if self.logger and self.logger.error then
        self.logger:error("Message queue was corrupted and has been reset.", { queue = queueName })
    end

    queue = {}
    self[queueName] = queue
    return queue
end

function MessageBus.new(logger)
    return setmetatable({
        outbound = {},
        inbound = {},
        bridgeOnline = false,
        lastHeartbeatUtc = nil,
        logger = logger,
    }, MessageBus)
end

function MessageBus:setBridgeOnline(isOnline, heartbeatUtc)
    self.bridgeOnline = isOnline == true
    if heartbeatUtc ~= nil then
        if type(heartbeatUtc) == "string" and heartbeatUtc ~= "" then
            self.lastHeartbeatUtc = heartbeatUtc
        elseif self.logger and self.logger.warn then
            self.logger:warn("Ignored invalid bridge heartbeat timestamp.", { heartbeatUtc = heartbeatUtc })
        end
    end
end

function MessageBus:enqueueOutbound(payload)
    if type(payload) ~= "table" then
        if self.logger and self.logger.warn then
            self.logger:warn("Rejected outbound payload because it was not a table.")
        end

        return false
    end

    table.insert(getQueue(self, "outbound"), payload)
    return true
end

function MessageBus:enqueueInbound(payload)
    if type(payload) ~= "table" then
        if self.logger and self.logger.warn then
            self.logger:warn("Rejected inbound payload because it was not a table.")
        end

        return false
    end

    table.insert(getQueue(self, "inbound"), payload)
    return true
end

function MessageBus:drainOutbound()
    local drained = getQueue(self, "outbound")
    self.outbound = {}
    return drained
end

function MessageBus:drainInbound()
    local drained = getQueue(self, "inbound")
    self.inbound = {}
    return drained
end

function MessageBus:getStatus()
    local outbound = getQueue(self, "outbound")
    local inbound = getQueue(self, "inbound")
    return {
        bridgeOnline = self.bridgeOnline,
        lastHeartbeatUtc = self.lastHeartbeatUtc,
        outboundQueued = #outbound,
        inboundQueued = #inbound,
    }
end

return MessageBus
