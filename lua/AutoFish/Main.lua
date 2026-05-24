local addonInfo, privateVars = ...
privateVars = privateVars or {}

local addonIdentifier = (addonInfo and addonInfo.identifier) or "AutoFish"
local addonVersion = (addonInfo and addonInfo.version) or "0.1.0"

local REFRESH_INTERVAL = 1.0
local MAX_MATCHES = 6

local Console = {}
local AutoFishLive = {}
privateVars.AutoFishLive = AutoFishLive

local state = nil
local runtime = {
  started = false,
  dirty = true,
  pendingReason = "startup",
  lastRefreshAt = 0,
}

local POLE_KEYWORDS = { "fishing", "pole", "rod" }
local BAIT_KEYWORDS = { "bait", "lure" }

local function now()
  if Inspect and Inspect.Time and Inspect.Time.Real then
    return Inspect.Time.Real() or 0
  end

  return 0
end

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

local function countEntries(value)
  if type(value) ~= "table" then
    return 0
  end

  local count = 0
  for _ in pairs(value) do
    count = count + 1
  end

  return count
end

local function toNumber(value)
  return tonumber(value)
end

local function toString(value)
  if value == nil then
    return nil
  end

  return tostring(value)
end

local function lower(value)
  if value == nil then
    return ""
  end

  return string.lower(tostring(value))
end

local function containsText(haystack, needle)
  if haystack == nil or needle == nil then
    return false
  end

  return string.find(lower(haystack), lower(needle), 1, true) ~= nil
end

local function trimText(value, maxLength)
  local text = tostring(value or "")
  if string.len(text) <= maxLength then
    return text
  end

  return string.sub(text, 1, maxLength - 3) .. "..."
end

local function shallowCopy(source)
  local target = {}

  if type(source) ~= "table" then
    return target
  end

  for key, value in pairs(source) do
    target[key] = value
  end

  return target
end

function Console.Write(message, color)
  local text = tostring(message or "")

  if Command and Command.Console and Command.Console.Display then
    local prefix = "<font color='" .. tostring(color or "#66CCFF") .. "'>[AutoFish]</font> "
    Command.Console.Display("general", true, prefix .. text, true)
    return
  end

  print("[AutoFish] " .. text)
end

local function ensureState()
  if type(AutoFish_State) ~= "table" then
    AutoFish_State = {}
  end

  state = AutoFish_State
  state.session = type(state.session) == "table" and state.session or {}
  state.current = type(state.current) == "table" and state.current or {}
  state.session.version = addonVersion
  state.session.startedAt = toNumber(state.session.startedAt) or now()
  state.session.refreshCount = toNumber(state.session.refreshCount) or 0
  state.session.lastReason = toString(state.session.lastReason) or "none"
  return state
end

local function buildSlotInfo(slot)
  local slotType, parameterA, parameterB = nil, nil, nil

  if Utility and Utility.Item and Utility.Item.Slot and Utility.Item.Slot.Parse then
    slotType, parameterA, parameterB = safeCall(Utility.Item.Slot.Parse, slot)
  end

  return {
    raw = toString(slot),
    slotType = toString(slotType),
    parameterA = parameterA,
    parameterB = parameterB,
  }
end

local function resolveItemDetail(details, itemId, slot)
  if type(details) ~= "table" then
    return nil
  end

  local direct = details[itemId]
  if type(direct) == "table" then
    return direct
  end

  direct = details[slot]
  if type(direct) == "table" then
    return direct
  end

  for _, value in pairs(details) do
    if type(value) == "table" then
      if value.id == itemId or value.id == slot then
        return value
      end
    end
  end

  return nil
end

local function collectItemEntries(slotSpecifier, source)
  local items = safeCall(Inspect.Item.List, slotSpecifier)
  if type(items) ~= "table" then
    return {}
  end

  local details = safeCall(Inspect.Item.Detail, items)
  local entries = {}

  for slot, itemId in pairs(items) do
    local detail = resolveItemDetail(details, itemId, slot) or {}

    entries[#entries + 1] = {
      source = source,
      slot = toString(slot),
      slotInfo = buildSlotInfo(slot),
      itemId = toString(itemId),
      id = toString(detail.id or itemId),
      name = toString(detail.name),
      category = toString(detail.category),
      typeName = toString(detail.type),
      description = toString(detail.description),
      stack = toNumber(detail.stack),
      slots = toNumber(detail.slots),
      cooldown = toNumber(detail.cooldown),
      cooldownRemaining = toNumber(detail.cooldownRemaining),
      requiredSkill = toString(detail.requiredSkill),
      icon = toString(detail.icon),
    }
  end

  table.sort(entries, function(left, right)
    local leftName = lower(left and left.name)
    local rightName = lower(right and right.name)

    if leftName ~= rightName then
      return leftName < rightName
    end

    return tostring(left and left.slot or "") < tostring(right and right.slot or "")
  end)

  return entries
end

local function buildMatchText(entry)
  local parts = {
    trimText(entry.name or entry.itemId or "unknown", 44),
    "[" .. tostring(entry.source or "?") .. "]",
    "slot=" .. tostring(entry.slot or "?"),
  }

  if entry.stack ~= nil then
    parts[#parts + 1] = "x" .. tostring(entry.stack)
  end

  return table.concat(parts, " ")
end

local function keywordScore(entry, keywords)
  if type(entry) ~= "table" or type(keywords) ~= "table" then
    return 0
  end

  local score = 0
  local haystack = table.concat({
    lower(entry.name),
    lower(entry.category),
    lower(entry.typeName),
    lower(entry.description),
    lower(entry.requiredSkill),
  }, " ")

  for _, keyword in ipairs(keywords) do
    if string.find(haystack, lower(keyword), 1, true) then
      if keyword == "fishing" then
        score = score + 12
      elseif keyword == "pole" or keyword == "rod" then
        score = score + 8
      elseif keyword == "bait" or keyword == "lure" then
        score = score + 6
      else
        score = score + 4
      end
    end
  end

  return score
end

local function collectMatches(entries, keywords, limit)
  local matches = {}

  if type(entries) ~= "table" then
    return matches
  end

  for _, entry in ipairs(entries) do
    local score = keywordScore(entry, keywords)
    if score > 0 then
      local match = shallowCopy(entry)
      match.matchScore = score
      match.matchText = buildMatchText(match)
      matches[#matches + 1] = match
    end
  end

  table.sort(matches, function(left, right)
    if (left.matchScore or 0) ~= (right.matchScore or 0) then
      return (left.matchScore or 0) > (right.matchScore or 0)
    end

    if tostring(left.source or "") ~= tostring(right.source or "") then
      return tostring(left.source or "") < tostring(right.source or "")
    end

    return tostring(left.name or left.itemId or "") < tostring(right.name or right.itemId or "")
  end)

  local maxCount = math.min(#matches, limit or MAX_MATCHES)
  local trimmed = {}
  for index = 1, maxCount do
    trimmed[index] = matches[index]
  end

  return trimmed
end

local function collectBagSummaries()
  if not (Utility and Utility.Item and Utility.Item.Slot and Utility.Item.Slot.Inventory) then
    return {}, 0
  end

  local bagSlotSpecifier = safeCall(Utility.Item.Slot.Inventory, "bag")
  local bagEntries = collectItemEntries(bagSlotSpecifier, "bag")
  local knownContainerSlots = 0

  for index, bagEntry in ipairs(bagEntries) do
    bagEntry.containerIndex = index
    bagEntry.displayName = bagEntry.name or ("Inventory Bag " .. tostring(index))

    if bagEntry.slots ~= nil then
      knownContainerSlots = knownContainerSlots + bagEntry.slots
    end

    local contentSlotSpecifier = safeCall(Utility.Item.Slot.Inventory, index)
    local contentItems = safeCall(Inspect.Item.List, contentSlotSpecifier)
    local usedSlots = countEntries(contentItems)

    bagEntry.usedSlots = usedSlots
    if bagEntry.slots ~= nil then
      bagEntry.freeSlots = math.max(0, bagEntry.slots - usedSlots)
    end
  end

  return bagEntries, knownContainerSlots
end

local function collectBuffEntries(unit)
  local buffIds = safeCall(Inspect.Buff.List, unit)
  if type(buffIds) ~= "table" then
    return {}
  end

  local details = safeCall(Inspect.Buff.Detail, unit, buffIds)
  if type(details) ~= "table" then
    return {}
  end

  local entries = {}

  for _, detail in pairs(details) do
    if type(detail) == "table" then
      entries[#entries + 1] = {
        name = toString(detail.name),
        debuff = detail.debuff and true or false,
        remaining = toNumber(detail.remaining),
        stack = toNumber(detail.stack),
      }
    end
  end

  table.sort(entries, function(left, right)
    return tostring(left.name or "") < tostring(right.name or "")
  end)

  return entries
end

local function findTrackFish(buffs)
  for _, buff in ipairs(buffs or {}) do
    if not buff.debuff and containsText(buff.name, "track fish") then
      return buff
    end
  end

  return nil
end

local function buildPlayerSnapshot()
  local playerUnit = safeCall(Inspect.Unit.Lookup, "player")
  local details = playerUnit and safeCall(Inspect.Unit.Detail, playerUnit) or nil

  if type(details) ~= "table" then
    return {
      available = false,
      playerUnit = toString(playerUnit),
    }, playerUnit
  end

  return {
    available = true,
    playerUnit = toString(playerUnit),
    name = toString(details.name),
    level = toNumber(details.level),
    role = toString(details.role),
    combat = details.combat and true or false,
    pvp = details.pvp and true or false,
    zone = toString(details.zone),
    locationName = toString(details.locationName),
    health = toNumber(details.health),
    healthMax = toNumber(details.healthMax),
    mana = toNumber(details.mana),
    manaMax = toNumber(details.manaMax),
    energy = toNumber(details.energy),
    energyMax = toNumber(details.energyMax),
    coord = {
      x = toNumber(details.coordX),
      y = toNumber(details.coordY),
      z = toNumber(details.coordZ),
    },
  }, playerUnit
end

local function buildCastbarSnapshot(playerUnit)
  local castbar = playerUnit and safeCall(Inspect.Unit.Castbar, playerUnit) or nil
  if type(castbar) ~= "table" then
    return {
      active = false,
    }
  end

  return {
    active = true,
    abilityName = toString(castbar.abilityName),
    remaining = toNumber(castbar.remaining),
    duration = toNumber(castbar.duration),
    channeled = castbar.channeled and true or false,
    uninterruptible = castbar.uninterruptible and true or false,
  }
end

local function buildSnapshot(reason)
  local player, playerUnit = buildPlayerSnapshot()
  local equipmentSpecifier = Utility and Utility.Item and Utility.Item.Slot and Utility.Item.Slot.Equipment and safeCall(Utility.Item.Slot.Equipment) or nil
  local inventorySpecifier = Utility and Utility.Item and Utility.Item.Slot and Utility.Item.Slot.Inventory and safeCall(Utility.Item.Slot.Inventory) or nil

  local equipmentEntries = collectItemEntries(equipmentSpecifier, "equipment")
  local inventoryEntries = collectItemEntries(inventorySpecifier, "inventory")
  local bagSummaries, knownContainerSlots = collectBagSummaries()

  local allEntries = {}
  for _, entry in ipairs(equipmentEntries) do
    allEntries[#allEntries + 1] = entry
  end
  for _, entry in ipairs(inventoryEntries) do
    allEntries[#allEntries + 1] = entry
  end

  local poleCandidates = collectMatches(allEntries, POLE_KEYWORDS, MAX_MATCHES)
  local baitCandidates = collectMatches(inventoryEntries, BAIT_KEYWORDS, MAX_MATCHES)
  local buffs = collectBuffEntries(playerUnit or "player")
  local trackFishBuff = findTrackFish(buffs)

  local equippedPole = nil
  local inventoryPole = nil
  for _, candidate in ipairs(poleCandidates) do
    if candidate.source == "equipment" and equippedPole == nil then
      equippedPole = candidate
    elseif candidate.source == "inventory" and inventoryPole == nil then
      inventoryPole = candidate
    end
  end

  local estimatedFreeSlots = nil
  if knownContainerSlots > 0 then
    estimatedFreeSlots = math.max(0, knownContainerSlots - #inventoryEntries)
  end

  return {
    capturedAt = now(),
    reason = toString(reason) or "unspecified",
    secureMode = Inspect and Inspect.System and Inspect.System.Secure and Inspect.System.Secure() and true or false,
    player = player,
    castbar = buildCastbarSnapshot(playerUnit),
    inventory = {
      itemCount = #inventoryEntries,
      equipmentCount = #equipmentEntries,
      bagCount = #bagSummaries,
      knownContainerSlots = knownContainerSlots,
      estimatedFreeSlots = estimatedFreeSlots,
      bagSummaries = bagSummaries,
    },
    fishing = {
      trackFishBuff = trackFishBuff,
      equippedPole = equippedPole,
      inventoryPole = inventoryPole,
      poleCandidates = poleCandidates,
      baitCandidates = baitCandidates,
    },
  }
end

local function queueRefresh(reason)
  runtime.dirty = true
  runtime.pendingReason = toString(reason) or runtime.pendingReason or "event"
end

function AutoFishLive.Refresh(reason, incrementCount)
  ensureState()

  local snapshot = buildSnapshot(reason or runtime.pendingReason or "manual")

  if incrementCount ~= false then
    state.session.refreshCount = (toNumber(state.session.refreshCount) or 0) + 1
  end

  snapshot.refreshCount = state.session.refreshCount
  state.current = snapshot
  state.session.lastCapturedAt = snapshot.capturedAt
  state.session.lastReason = snapshot.reason

  runtime.lastRefreshAt = snapshot.capturedAt or now()
  runtime.pendingReason = nil
  runtime.dirty = false

  return snapshot
end

local function candidateText(candidate)
  if type(candidate) ~= "table" then
    return "none"
  end

  return candidate.matchText or buildMatchText(candidate)
end

local function printCandidateList(title, candidates, emptyMessage)
  Console.Write(title, "#FFFF88")

  if type(candidates) ~= "table" or #candidates == 0 then
    Console.Write(emptyMessage or "  none", "#FFAA44")
    return
  end

  for index, candidate in ipairs(candidates) do
    Console.Write("  " .. tostring(index) .. ". " .. candidateText(candidate), "#CCCCCC")
  end
end

function AutoFishLive.PrintStatus()
  local snapshot = AutoFishLive.Refresh("slash.status", true)
  local player = snapshot.player or {}

  if not player.available then
    Console.Write("Player unit is not ready yet. Addon loaded, but live player data is unavailable.", "#FFAA44")
    return
  end

  local zoneText = trimText(player.locationName or player.zone or "unknown", 42)
  Console.Write(
    string.format(
      "player=%s Lv%s zone=%s",
      tostring(player.name or "?"),
      tostring(player.level or "?"),
      zoneText),
    "#00CC88")

  Console.Write(
    string.format(
      "combat=%s secure=%s items=%s bags=%s knownSlots=%s estFree=%s",
      tostring(player.combat and true or false),
      tostring(snapshot.secureMode and true or false),
      tostring(snapshot.inventory.itemCount or 0),
      tostring(snapshot.inventory.bagCount or 0),
      tostring(snapshot.inventory.knownContainerSlots or 0),
      tostring(snapshot.inventory.estimatedFreeSlots ~= nil and snapshot.inventory.estimatedFreeSlots or "?")),
    "#66CCFF")

  Console.Write("pole=" .. candidateText(snapshot.fishing.equippedPole or snapshot.fishing.inventoryPole), "#CCCCCC")

  if snapshot.fishing.trackFishBuff then
    Console.Write("track fish buff detected: " .. tostring(snapshot.fishing.trackFishBuff.name), "#00CC88")
  else
    Console.Write("track fish buff not detected.", "#FFAA44")
  end

  if snapshot.castbar and snapshot.castbar.active then
    Console.Write(
      string.format(
        "castbar=%s remaining=%s/%s",
        tostring(snapshot.castbar.abilityName or "?"),
        tostring(snapshot.castbar.remaining or "?"),
        tostring(snapshot.castbar.duration or "?")),
      "#CCCCCC")
  end
end

function AutoFishLive.PrintBags()
  local snapshot = AutoFishLive.Refresh("slash.bags", true)
  local bags = snapshot.inventory and snapshot.inventory.bagSummaries or {}

  Console.Write("Bag probe:", "#FFFF88")

  if type(bags) ~= "table" or #bags == 0 then
    Console.Write("  No bag containers were discovered via Utility.Item.Slot.Inventory(\"bag\").", "#FFAA44")
    return
  end

  for _, bag in ipairs(bags) do
    Console.Write(
      string.format(
        "  #%s %s slots=%s used=%s free=%s",
        tostring(bag.containerIndex or "?"),
        trimText(bag.displayName or bag.name or "unknown", 30),
        tostring(bag.slots or "?"),
        tostring(bag.usedSlots or 0),
        tostring(bag.freeSlots ~= nil and bag.freeSlots or "?")),
      "#CCCCCC")
  end
end

function AutoFishLive.PrintInventory()
  local snapshot = AutoFishLive.Refresh("slash.inventory", true)

  Console.Write(
    string.format(
      "Inventory summary: items=%s equipment=%s knownSlots=%s estFree=%s",
      tostring(snapshot.inventory.itemCount or 0),
      tostring(snapshot.inventory.equipmentCount or 0),
      tostring(snapshot.inventory.knownContainerSlots or 0),
      tostring(snapshot.inventory.estimatedFreeSlots ~= nil and snapshot.inventory.estimatedFreeSlots or "?")),
    "#66CCFF")

  printCandidateList("Bait / lure candidates:", snapshot.fishing.baitCandidates, "  No bait/lure candidates matched the current inventory scan.")
end

function AutoFishLive.PrintPoleCandidates()
  local snapshot = AutoFishLive.Refresh("slash.pole", true)
  printCandidateList("Fishing pole candidates:", snapshot.fishing.poleCandidates, "  No fishing-pole candidates matched equipped or carried items.")
end

function AutoFishLive.PrintHelp()
  Console.Write("Commands:", "#FFFF88")
  Console.Write("  /autofish status    - show player, zone, secure state, and inventory summary", "#CCCCCC")
  Console.Write("  /autofish bags      - inspect bag containers and used/free slot counts", "#CCCCCC")
  Console.Write("  /autofish inventory - inspect bait/lure-related inventory candidates", "#CCCCCC")
  Console.Write("  /autofish pole      - search equipped and carried fishing-pole candidates", "#CCCCCC")
  Console.Write("  /autofish snapshot  - refresh the saved snapshot without extra output", "#CCCCCC")
  Console.Write("  /autofish help      - show this help", "#CCCCCC")
end

function AutoFishLive.OnSlashCommand(args)
  local command = string.match(args or "", "^(%S+)")
  if command then
    command = string.lower(command)
  end

  if not command or command == "help" then
    AutoFishLive.PrintHelp()
    return
  end

  if command == "status" then
    AutoFishLive.PrintStatus()
    return
  end

  if command == "bags" then
    AutoFishLive.PrintBags()
    return
  end

  if command == "inventory" then
    AutoFishLive.PrintInventory()
    return
  end

  if command == "pole" then
    AutoFishLive.PrintPoleCandidates()
    return
  end

  if command == "snapshot" then
    AutoFishLive.Refresh("slash.snapshot", true)
    Console.Write("Snapshot refreshed.", "#00CC88")
    return
  end

  Console.Write("Unknown command. Use /autofish help.", "#FF4444")
end

function AutoFishLive.OnSavedVariablesLoad(addon)
  if addon ~= addonIdentifier then
    return
  end

  ensureState()
end

function AutoFishLive.OnSavedVariablesSave(addon)
  if addon ~= addonIdentifier then
    return
  end

  ensureState()
  AutoFishLive.Refresh("save-begin", false)
  AutoFish_State = state
end

function AutoFishLive.OnStartup()
  ensureState()
  runtime.started = true
  AutoFishLive.Refresh("startup", true)
  Console.Write("Loaded. Use /autofish help to inspect fishing-readiness signals.", "#00CC88")
end

function AutoFishLive.OnUpdateEnd()
  if not runtime.started then
    return
  end

  local currentTime = now()
  if runtime.dirty or (currentTime - runtime.lastRefreshAt) >= REFRESH_INTERVAL then
    AutoFishLive.Refresh(runtime.pendingReason or "heartbeat", false)
  end
end

local function attach(eventTable, handler, label)
  if type(eventTable) ~= "table" then
    return
  end

  table.insert(eventTable, { handler, addonIdentifier, label })
end

attach(Command.Slash.Register("autofish"), AutoFishLive.OnSlashCommand, "AutoFish slash command")

attach(Event.Addon.SavedVariables.Load.End, AutoFishLive.OnSavedVariablesLoad, "AutoFish load saved variables")
attach(Event.Addon.SavedVariables.Save.Begin, AutoFishLive.OnSavedVariablesSave, "AutoFish save saved variables")
attach(Event.Addon.Startup.End, AutoFishLive.OnStartup, "AutoFish startup")
attach(Event.System.Update.End, AutoFishLive.OnUpdateEnd, "AutoFish update")
attach(Event.Item.Slot, function() queueRefresh("event.item_slot") end, "AutoFish item slot change")
attach(Event.Item.Update, function() queueRefresh("event.item_update") end, "AutoFish item update")
attach(Event.System.Secure.Enter, function() queueRefresh("event.secure_enter") end, "AutoFish secure enter")
attach(Event.System.Secure.Leave, function() queueRefresh("event.secure_leave") end, "AutoFish secure leave")
