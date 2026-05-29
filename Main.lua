-- AutoFishChatCopy Main.lua
-- Version: 0.1.0
-- Total character count: 15533
-- Purpose: Capture future Rift chat notifications into a bounded buffer and present copy-ready text in a selectable UI text field.
-- Notes: Rift addons are sandboxed; this addon does not claim direct Windows clipboard access.

local addonInfo, privateVars = ...
privateVars = privateVars or {}

local IDENTIFIER = (addonInfo and addonInfo.identifier) or "AutoFishChatCopy"
local VERSION = (addonInfo and addonInfo.version) or "0.1.0"

local MAX_LINES = 200
local DEFAULT_EXPORT_LINES = 40
local MAX_ARG_CHARS = 700
local MAX_TABLE_FIELDS = 18
local MAX_EXPORT_CHARS = 14000

local state = nil
local ui = {
  context = nil,
  root = nil,
  title = nil,
  help = nil,
  field = nil,
  status = nil,
}

local function safeCall(fn, ...)
  if type(fn) ~= "function" then
    return nil
  end

  local ok, a, b, c, d = pcall(fn, ...)
  if not ok then
    return nil
  end

  return a, b, c, d
end

local function now()
  if Inspect and Inspect.Time and Inspect.Time.Real then
    return Inspect.Time.Real() or 0
  end

  return 0
end

local function wallClock()
  if os and os.date then
    local ok, value = pcall(os.date, "%H:%M:%S")
    if ok and value then
      return tostring(value)
    end
  end

  return string.format("%.2f", now())
end

local function trim(value, maxLength)
  local text = tostring(value or "")
  if string.len(text) <= maxLength then
    return text
  end

  return string.sub(text, 1, math.max(1, maxLength - 3)) .. "..."
end

local function cleanScalar(value)
  local text = tostring(value or "")
  text = string.gsub(text, "\r\n", "\n")
  text = string.gsub(text, "\r", "\n")
  text = string.gsub(text, "[%z\1-\8\11\12\14-\31]", " ")
  return trim(text, MAX_ARG_CHARS)
end

local function sortedKeys(source)
  local keys = {}
  if type(source) ~= "table" then
    return keys
  end

  for key in pairs(source) do
    keys[#keys + 1] = key
  end

  table.sort(keys, function(left, right)
    return tostring(left) < tostring(right)
  end)

  return keys
end

local function valueToText(value, depth)
  local valueType = type(value)
  if value == nil then
    return "nil"
  end

  if valueType ~= "table" then
    return cleanScalar(value)
  end

  if depth and depth > 1 then
    return "table(" .. tostring(#sortedKeys(value)) .. ")"
  end

  local keys = sortedKeys(value)
  local parts = {}
  local limit = math.min(#keys, MAX_TABLE_FIELDS)
  for index = 1, limit do
    local key = keys[index]
    parts[#parts + 1] = tostring(key) .. "=" .. valueToText(value[key], (depth or 0) + 1)
  end

  if #keys > limit then
    parts[#parts + 1] = "...+" .. tostring(#keys - limit)
  end

  return "{" .. table.concat(parts, " ") .. "}"
end

local function write(message, color)
  local text = tostring(message or "")
  if Command and Command.Console and Command.Console.Display then
    Command.Console.Display("general", true, "<font color='" .. tostring(color or "#66CCFF") .. "'>[AF Copy]</font> " .. text, true)
    return
  end

  print("[AF Copy] " .. text)
end

local function ensureState()
  if type(AutoFishChatCopy_State) ~= "table" then
    AutoFishChatCopy_State = {}
  end

  state = AutoFishChatCopy_State
  state.enabled = state.enabled ~= false
  state.sequence = tonumber(state.sequence) or 0
  state.markSequence = tonumber(state.markSequence) or nil
  state.lines = type(state.lines) == "table" and state.lines or {}
  state.lastExport = type(state.lastExport) == "string" and state.lastExport or ""
  state.loadedVersion = VERSION
  return state
end

local function pushLine(source, text)
  ensureState()
  if state.enabled ~= true then
    return
  end

  state.sequence = (tonumber(state.sequence) or 0) + 1
  local entry = {
    sequence = state.sequence,
    source = tostring(source or "chat"),
    timestamp = wallClock(),
    text = cleanScalar(text),
  }

  state.lines[#state.lines + 1] = entry
  while #state.lines > MAX_LINES do
    table.remove(state.lines, 1)
  end

  AutoFishChatCopy_State = state
end

local function formatEventLine(...)
  local count = select("#", ...)
  local parts = {}
  for index = 1, count do
    local value = select(index, ...)
    parts[#parts + 1] = "arg" .. tostring(index) .. "=" .. valueToText(value, 0)
  end

  if #parts == 0 then
    return "(empty chat event)"
  end

  return table.concat(parts, " | ")
end

local function onNamedChatEvent(source, ...)
  pushLine(source, formatEventLine(...))
end

local function onSystemError(...)
  pushLine("Event.System.Error", formatEventLine(...))
end

local function lineToExport(entry)
  return string.format(
    "[%s #%s %s] %s",
    tostring(entry.timestamp or "?"),
    tostring(entry.sequence or "?"),
    tostring(entry.source or "chat"),
    tostring(entry.text or "")
  )
end

local function buildExport(mode, count)
  ensureState()

  local exportLines = {}
  local requested = tonumber(count) or DEFAULT_EXPORT_LINES
  if requested < 1 then
    requested = DEFAULT_EXPORT_LINES
  end

  if mode == "since" then
    local mark = tonumber(state.markSequence) or 0
    for _, entry in ipairs(state.lines) do
      if (tonumber(entry.sequence) or 0) > mark then
        exportLines[#exportLines + 1] = lineToExport(entry)
      end
    end
  elseif mode == "all" then
    for _, entry in ipairs(state.lines) do
      exportLines[#exportLines + 1] = lineToExport(entry)
    end
  else
    local startIndex = math.max(1, #state.lines - requested + 1)
    for index = startIndex, #state.lines do
      exportLines[#exportLines + 1] = lineToExport(state.lines[index])
    end
  end

  local text = table.concat(exportLines, "\n")
  if string.len(text) > MAX_EXPORT_CHARS then
    text = string.sub(text, string.len(text) - MAX_EXPORT_CHARS + 1)
    text = "[trimmed to last " .. tostring(MAX_EXPORT_CHARS) .. " chars]\n" .. text
  end

  if text == "" then
    text = "(AutoFishChatCopy has no captured chat yet. It captures future chat events after the addon is loaded.)"
  end

  state.lastExport = text
  AutoFishChatCopy_State = state
  return text, #exportLines
end

local function frameCall(frame, method, ...)
  if type(frame) ~= "table" or type(frame[method]) ~= "function" then
    return false
  end

  local ok = pcall(frame[method], frame, ...)
  return ok == true
end

local function createFrame(kind, name, parent)
  if not (UI and UI.CreateFrame) then
    return nil
  end

  local ok, frame = pcall(UI.CreateFrame, kind, name, parent)
  if ok and frame then
    return frame
  end

  return nil
end

local function ensureUi()
  if ui.root then
    return ui.field ~= nil
  end

  if not (UI and UI.CreateContext and UI.CreateFrame) then
    return false
  end

  local context = safeCall(UI.CreateContext, "AutoFishChatCopyContext")
  if not context then
    return false
  end

  ui.context = context
  ui.root = createFrame("Frame", "AutoFishChatCopyRoot", context)
  if not ui.root then
    return false
  end

  frameCall(ui.root, "SetPoint", "TOPLEFT", UIParent, "TOPLEFT", 90, 90)
  frameCall(ui.root, "SetWidth", 760)
  frameCall(ui.root, "SetHeight", 410)
  frameCall(ui.root, "SetLayer", 9000)
  frameCall(ui.root, "SetBackgroundColor", 0, 0, 0, 0.88)

  ui.title = createFrame("Text", "AutoFishChatCopyTitle", ui.root)
  if ui.title then
    frameCall(ui.title, "SetPoint", "TOPLEFT", ui.root, "TOPLEFT", 12, 8)
    frameCall(ui.title, "SetText", "AutoFish Chat Copy")
    frameCall(ui.title, "SetFontSize", 18)
  end

  ui.help = createFrame("Text", "AutoFishChatCopyHelp", ui.root)
  if ui.help then
    frameCall(ui.help, "SetPoint", "TOPLEFT", ui.root, "TOPLEFT", 12, 34)
    frameCall(ui.help, "SetText", "Click the text box, press Ctrl+A, then Ctrl+C. Paste into ChatGPT.")
    frameCall(ui.help, "SetFontSize", 14)
  end

  local fieldKinds = { "RiftTextfield", "Textfield", "TextArea", "RiftTextArea" }
  for _, kind in ipairs(fieldKinds) do
    ui.field = createFrame(kind, "AutoFishChatCopyField", ui.root)
    if ui.field then
      break
    end
  end

  if not ui.field then
    return false
  end

  frameCall(ui.field, "SetPoint", "TOPLEFT", ui.root, "TOPLEFT", 12, 64)
  frameCall(ui.field, "SetWidth", 736)
  frameCall(ui.field, "SetHeight", 300)

  ui.status = createFrame("Text", "AutoFishChatCopyStatus", ui.root)
  if ui.status then
    frameCall(ui.status, "SetPoint", "TOPLEFT", ui.root, "TOPLEFT", 12, 372)
    frameCall(ui.status, "SetFontSize", 13)
  end

  frameCall(ui.root, "SetVisible", false)
  return true
end

local function showCopyWindow(text, statusText)
  local ok = ensureUi()
  if not ok then
    write("Copy UI unavailable. Try /afcopy status; this Rift build may not expose a usable text input frame.", "#FFAA44")
    write("Captured lines are stored in AutoFishChatCopy_State after reload/logout.", "#CCCCCC")
    return false
  end

  frameCall(ui.field, "SetText", text)
  frameCall(ui.status, "SetText", tostring(statusText or "Ready."))
  frameCall(ui.root, "SetVisible", true)
  frameCall(ui.field, "SetKeyFocus", true)

  if type(ui.field.SelectAll) == "function" then
    pcall(ui.field.SelectAll, ui.field)
  elseif type(ui.field.SetSelection) == "function" then
    pcall(ui.field.SetSelection, ui.field, 0, string.len(text))
  end

  return true
end

local function hideCopyWindow()
  if ui.root then
    frameCall(ui.root, "SetVisible", false)
  end
end

local function parseArgs(args)
  local words = {}
  for word in string.gmatch(tostring(args or ""), "%S+") do
    words[#words + 1] = string.lower(word)
  end

  return words
end

local function printHelp()
  write("Commands:", "#FFFF88")
  write("  /afcopy                 - copy-ready last 40 captured chat events", "#CCCCCC")
  write("  /afcopy last <n>        - copy-ready last n captured events", "#CCCCCC")
  write("  /afcopy since           - copy-ready events since /afcopy mark", "#CCCCCC")
  write("  /afcopy all             - copy-ready full bounded buffer", "#CCCCCC")
  write("  /afcopy mark            - mark current position", "#CCCCCC")
  write("  /afcopy clear           - clear captured buffer", "#CCCCCC")
  write("  /afcopy on|off|status   - control capture", "#CCCCCC")
  write("  /afcopy hide            - hide copy window", "#CCCCCC")
  write("Clipboard note: addons cannot reliably write Windows clipboard directly; use Ctrl+A/C in the copy box.", "#FFAA44")
end

local function printStatus()
  ensureState()
  write(
    string.format(
      "status enabled=%s lines=%s seq=%s mark=%s version=%s",
      tostring(state.enabled == true),
      tostring(#state.lines),
      tostring(state.sequence or 0),
      tostring(state.markSequence or "-"),
      tostring(VERSION)
    ),
    "#66CCFF"
  )
end

local function handleCommand(handle, args)
  local argsText = args
  if argsText == nil and type(handle) == "string" then
    argsText = handle
  end

  local words = parseArgs(argsText)
  local command = words[1] or "last"

  ensureState()

  if command == "help" or command == "?" then
    printHelp()
    return
  end

  if command == "status" then
    printStatus()
    return
  end

  if command == "on" or command == "enable" then
    state.enabled = true
    AutoFishChatCopy_State = state
    write("Capture enabled.", "#00CC88")
    return
  end

  if command == "off" or command == "disable" then
    state.enabled = false
    AutoFishChatCopy_State = state
    write("Capture disabled.", "#FFAA44")
    return
  end

  if command == "clear" then
    state.lines = {}
    state.sequence = 0
    state.markSequence = nil
    state.lastExport = ""
    AutoFishChatCopy_State = state
    write("Captured chat buffer cleared.", "#00CC88")
    return
  end

  if command == "mark" then
    state.markSequence = tonumber(state.sequence) or 0
    AutoFishChatCopy_State = state
    write("Mark set at sequence " .. tostring(state.markSequence) .. ".", "#00CC88")
    return
  end

  if command == "hide" or command == "close" then
    hideCopyWindow()
    write("Copy window hidden.", "#CCCCCC")
    return
  end

  local mode = "last"
  local count = tonumber(words[2])

  if command == "all" then
    mode = "all"
  elseif command == "since" then
    mode = "since"
  elseif command == "last" or command == "copy" or command == "show" then
    mode = "last"
  elseif tonumber(command) ~= nil then
    count = tonumber(command)
    mode = "last"
  else
    write("Unknown command. Use /afcopy help.", "#FF4444")
    return
  end

  local text, exported = buildExport(mode, count)
  local status = string.format("Exported %s event(s). Click box, Ctrl+A, Ctrl+C.", tostring(exported))
  if showCopyWindow(text, status) then
    write(status, "#00CC88")
  end
end

local function resolveAddonArgument(first, second)
  if second ~= nil then
    return second
  end

  return first
end

local function onSavedVariablesLoad(handle, addon)
  addon = resolveAddonArgument(handle, addon)
  if addon ~= nil and addon ~= IDENTIFIER then
    return
  end

  ensureState()
end

local function onSavedVariablesSave(handle, addon)
  addon = resolveAddonArgument(handle, addon)
  if addon ~= nil and addon ~= IDENTIFIER then
    return
  end

  ensureState()
  AutoFishChatCopy_State = state
end

local function onStartup(handle, addon)
  addon = resolveAddonArgument(handle, addon)
  if addon ~= nil and addon ~= IDENTIFIER then
    return
  end

  ensureState()
  write("Loaded. Use /afcopy help. Captures future chat events only.", "#00CC88")
end

local function attach(eventTable, handler, label)
  if type(eventTable) ~= "table" then
    return false
  end

  if Command and Command.Event and Command.Event.Attach then
    local ok = pcall(Command.Event.Attach, eventTable, handler, label)
    return ok == true
  end

  table.insert(eventTable, { handler, IDENTIFIER, label })
  return true
end

local function registerSlash(name)
  if not (Command and Command.Slash and Command.Slash.Register) then
    return false
  end

  local slashEvent = safeCall(Command.Slash.Register, name)
  return attach(slashEvent, handleCommand, IDENTIFIER .. " slash " .. tostring(name))
end

local function attachChatEvents()
  local attached = 0

  if Event and Event.Chat then
    for name, eventTable in pairs(Event.Chat) do
      if type(eventTable) == "table" then
        local source = "Event.Chat." .. tostring(name)
        if attach(eventTable, function(...) onNamedChatEvent(source, ...) end, IDENTIFIER .. " " .. source) then
          attached = attached + 1
        end
      end
    end
  end

  if attached == 0 then
    attach(Event and Event.Chat and Event.Chat.Notify, function(...) onNamedChatEvent("Event.Chat.Notify", ...) end, IDENTIFIER .. " Event.Chat.Notify")
  end
end

registerSlash("afcopy")
registerSlash("chatcopy")

local addonEvents = Event and Event.Addon
local savedVariableEvents = addonEvents and addonEvents.SavedVariables
attach(savedVariableEvents and savedVariableEvents.Load and savedVariableEvents.Load.End, onSavedVariablesLoad, IDENTIFIER .. " saved variables load")
attach(savedVariableEvents and savedVariableEvents.Save and savedVariableEvents.Save.Begin, onSavedVariablesSave, IDENTIFIER .. " saved variables save")

local addonLoadEvent = addonEvents and addonEvents.Load and addonEvents.Load.End
if not addonLoadEvent and addonEvents and addonEvents.Startup then
  addonLoadEvent = addonEvents.Startup.End
end
attach(addonLoadEvent, onStartup, IDENTIFIER .. " startup")

attachChatEvents()
attach(Event and Event.System and Event.System.Error, onSystemError, IDENTIFIER .. " system error")

-- End of AutoFishChatCopy Main.lua
