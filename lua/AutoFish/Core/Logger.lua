local Logger = {}
Logger.__index = Logger

local function normalizeLevel(level)
    if type(level) ~= "string" then
        return "info"
    end

    local normalized = string.lower(level)
    if normalized == "debug" or normalized == "info" or normalized == "warn" or normalized == "error" then
        return normalized
    end

    return "info"
end

local function shallowCopy(value)
    if type(value) ~= "table" then
        return value
    end

    local copy = {}
    for key, item in pairs(value) do
        copy[key] = item
    end

    return copy
end

function Logger.new(options)
    options = type(options) == "table" and options or {}

    local maxEntries = tonumber(options.maxEntries) or 100
    maxEntries = math.max(1, math.floor(maxEntries))

    return setmetatable({
        entries = {},
        maxEntries = maxEntries,
        sink = type(options.sink) == "function" and options.sink or nil,
    }, Logger)
end

function Logger:log(level, message, context)
    local entry = {
        timestampUtc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
        level = normalizeLevel(level),
        message = type(message) == "string" and message ~= "" and message or "log entry emitted without a message",
        context = shallowCopy(context),
    }

    table.insert(self.entries, entry)
    if #self.entries > self.maxEntries then
        table.remove(self.entries, 1)
    end

    if self.sink then
        pcall(self.sink, entry)
    end

    return entry
end

function Logger:debug(message, context)
    return self:log("debug", message, context)
end

function Logger:info(message, context)
    return self:log("info", message, context)
end

function Logger:warn(message, context)
    return self:log("warn", message, context)
end

function Logger:error(message, context)
    return self:log("error", message, context)
end

function Logger:getEntries()
    local entries = {}
    for index, entry in ipairs(self.entries) do
        entries[index] = shallowCopy(entry)
    end

    return entries
end

function Logger:clear()
    self.entries = {}
end

AutoFish = AutoFish or {}
AutoFish.Core = AutoFish.Core or {}
AutoFish.Core.Logger = Logger
if require ~= nil then return Logger end
