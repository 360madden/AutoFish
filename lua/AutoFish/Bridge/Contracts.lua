local Contracts = {}

Contracts.ContractVersion = "1.0.0"

Contracts.CommandType = {
    START = "start",
    PAUSE = "pause",
    RESUME = "resume",
    STOP = "stop",
    SYNC_PROFILE = "sync_profile",
    REQUEST_SNAPSHOT = "request_snapshot",
    ACK = "ack",
}

Contracts.MessageType = {
    ACK = "ack",
    SESSION_STATUS = "session_status",
    COMMAND = "command",
}

Contracts.Mode = {
    IDLE = "idle",
    SCANNING = "scanning",
    CASTING = "casting",
    WAITING_BITE = "waiting_bite",
    HOOKING = "hooking",
    LOOTING = "looting",
    MAINTENANCE = "maintenance",
    RECOVERING = "recovering",
    PAUSED = "paused",
}

AutoFish = AutoFish or {}
AutoFish.Bridge = AutoFish.Bridge or {}
AutoFish.Bridge.Contracts = Contracts
if require ~= nil then return Contracts end
