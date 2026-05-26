local addonInfo, privateVars = ...
privateVars = privateVars or {}

local addonIdentifier = (addonInfo and addonInfo.identifier) or "AutoFish"
local addonVersion = (addonInfo and addonInfo.version) or "0.1.0"

local REFRESH_INTERVAL = 1.0
local MAX_MATCHES = 6
local MAX_TRACE_SAMPLES = 90

local Console = {}
local AutoFishLive = {}
privateVars.AutoFishLive = AutoFishLive

local state = nil
local runtime = {
  started = false,
  dirty = true,
  pendingReason = "startup",
  lastRefreshAt = 0,
  lastAbilityScanAt = 0,
  abilityCandidates = {},
  abilityScanError = nil,
}

local POLE_KEYWORDS = { "fishing", "pole", "rod" }
local BAIT_KEYWORDS = { "bait", "lure" }
local FISHING_ABILITY_KEYWORDS = { "fish", "fishing", "pole", "bait", "lure" }

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

local function collectAbilityMatches(keywords, limit)
  local matches = {}

  if not (Inspect and Inspect.Ability and Inspect.Ability.New and Inspect.Ability.New.List and Inspect.Ability.New.Detail) then
    return matches, "Inspect.Ability.New API unavailable"
  end

  local abilityList = safeCall(Inspect.Ability.New.List)
  if type(abilityList) ~= "table" then
    return matches, "Inspect.Ability.New.List returned no table"
  end

  local details = safeCall(Inspect.Ability.New.Detail, abilityList)
  if type(details) ~= "table" then
    details = {}
  end

  for abilityId in pairs(abilityList) do
    local detail = details[abilityId]
    if type(detail) ~= "table" then
      detail = safeCall(Inspect.Ability.New.Detail, abilityId)
    end

    if type(detail) == "table" then
      local entry = {
        id = toString(abilityId),
        name = toString(detail.name),
        description = toString(detail.description),
        category = toString(detail.category),
        icon = toString(detail.icon),
        requiredSkill = toString(detail.requiredSkill),
        rangeMax = toNumber(detail.rangeMax),
        castingTime = toNumber(detail.castingTime),
        cooldown = toNumber(detail.cooldown),
        currentCooldownRemaining = toNumber(detail.currentCooldownRemaining or detail.cooldownRemaining),
        unusable = detail.unusable and true or false,
        outOfRange = detail.outOfRange and true or false,
        passive = detail.passive and true or false,
        channeled = detail.channeled and true or false,
      }

      local score = keywordScore(entry, keywords)
      if score > 0 then
        entry.matchScore = score
        matches[#matches + 1] = entry
      end
    end
  end

  table.sort(matches, function(left, right)
    if (left.matchScore or 0) ~= (right.matchScore or 0) then
      return (left.matchScore or 0) > (right.matchScore or 0)
    end

    return tostring(left.name or left.id or "") < tostring(right.name or right.id or "")
  end)

  local maxCount = math.min(#matches, limit or MAX_MATCHES)
  local trimmed = {}
  for index = 1, maxCount do
    trimmed[index] = matches[index]
  end

  return trimmed, nil
end

local function getFishingAbilityCandidates(force)
  local currentTime = now()
  if not force and type(runtime.abilityCandidates) == "table" and (currentTime - (runtime.lastAbilityScanAt or 0)) < 10 then
    return runtime.abilityCandidates, runtime.abilityScanError
  end

  local candidates, errorText = collectAbilityMatches(FISHING_ABILITY_KEYWORDS, MAX_MATCHES)
  runtime.abilityCandidates = candidates
  runtime.abilityScanError = errorText
  runtime.lastAbilityScanAt = currentTime
  return candidates, errorText
end

local function collectUsableLureAbilities(abilityCandidates)
  local matches = {}
  if type(abilityCandidates) ~= "table" then
    return matches
  end

  for _, ability in ipairs(abilityCandidates) do
    local name = lower(ability.name)
    local category = lower(ability.category)
    local description = lower(ability.description)
    if (containsText(name, "lure") or containsText(category, "lure") or containsText(description, "lure"))
      and ability.unusable ~= true
      and ability.passive ~= true then
      matches[#matches + 1] = ability
    end
  end

  return matches
end

local function collectBagSummaries()
  if not (Utility and Utility.Item and Utility.Item.Slot and Utility.Item.Slot.Inventory) then
    return {}, 0, nil, nil
  end

  local bagSlotSpecifier = safeCall(Utility.Item.Slot.Inventory, "bag")
  local bagEntries = collectItemEntries(bagSlotSpecifier, "bag")
  local knownContainerSlots = 0
  local knownUsedSlots = 0
  local estimatedFreeSlots = 0
  local hasFreeSlotDetail = false

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
    knownUsedSlots = knownUsedSlots + usedSlots
    if bagEntry.slots ~= nil then
      bagEntry.freeSlots = math.max(0, bagEntry.slots - usedSlots)
      estimatedFreeSlots = estimatedFreeSlots + bagEntry.freeSlots
      hasFreeSlotDetail = true
    end
  end

  if not hasFreeSlotDetail then
    estimatedFreeSlots = nil
  end

  return bagEntries, knownContainerSlots, knownUsedSlots, estimatedFreeSlots
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

local function formatCoordValue(value)
  local numberValue = toNumber(value)
  if numberValue == nil then
    return "?"
  end

  return string.format("%.2f", numberValue)
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
  local bagSummaries, knownContainerSlots, knownUsedSlots, estimatedFreeSlots = collectBagSummaries()

  local allEntries = {}
  for _, entry in ipairs(equipmentEntries) do
    allEntries[#allEntries + 1] = entry
  end
  for _, entry in ipairs(inventoryEntries) do
    allEntries[#allEntries + 1] = entry
  end

  local poleCandidates = collectMatches(allEntries, POLE_KEYWORDS, MAX_MATCHES)
  local baitCandidates = collectMatches(inventoryEntries, BAIT_KEYWORDS, MAX_MATCHES)
  local abilityCandidates, abilityScanError = getFishingAbilityCandidates(false)
  local lureAbilityCandidates = collectUsableLureAbilities(abilityCandidates)
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
      knownUsedSlots = knownUsedSlots,
      estimatedFreeSlots = estimatedFreeSlots,
      bagSummaries = bagSummaries,
    },
    fishing = {
      trackFishBuff = trackFishBuff,
      equippedPole = equippedPole,
      inventoryPole = inventoryPole,
      poleCandidates = poleCandidates,
      baitCandidates = baitCandidates,
      abilityCandidates = abilityCandidates,
      abilityScanError = abilityScanError,
      lureAbilityCandidates = lureAbilityCandidates,
    },
  }
end

local function addObservationNote(notes, text)
  notes[#notes + 1] = tostring(text)
end

local function hasEntries(value)
  return type(value) == "table" and #value > 0
end

local function apiProbeEntry(name, available)
  return {
    name = name,
    available = available and true or false,
  }
end

local function collectApiProbe()
  return {
    apiProbeEntry("Command.Console.Display", Command and Command.Console and type(Command.Console.Display) == "function"),
    apiProbeEntry("Command.Event.Attach", Command and Command.Event and type(Command.Event.Attach) == "function"),
    apiProbeEntry("Command.Slash.Register", Command and Command.Slash and type(Command.Slash.Register) == "function"),
    apiProbeEntry("Inspect.Ability.New.List", Inspect and Inspect.Ability and Inspect.Ability.New and type(Inspect.Ability.New.List) == "function"),
    apiProbeEntry("Inspect.Ability.New.Detail", Inspect and Inspect.Ability and Inspect.Ability.New and type(Inspect.Ability.New.Detail) == "function"),
    apiProbeEntry("Inspect.Ability.List", Inspect and Inspect.Ability and type(Inspect.Ability.List) == "function"),
    apiProbeEntry("Inspect.Ability.Detail", Inspect and Inspect.Ability and type(Inspect.Ability.Detail) == "function"),
    apiProbeEntry("Inspect.Buff.List", Inspect and Inspect.Buff and type(Inspect.Buff.List) == "function"),
    apiProbeEntry("Inspect.Buff.Detail", Inspect and Inspect.Buff and type(Inspect.Buff.Detail) == "function"),
    apiProbeEntry("Inspect.Item.List", Inspect and Inspect.Item and type(Inspect.Item.List) == "function"),
    apiProbeEntry("Inspect.Item.Detail", Inspect and Inspect.Item and type(Inspect.Item.Detail) == "function"),
    apiProbeEntry("Inspect.Unit.Lookup", Inspect and Inspect.Unit and type(Inspect.Unit.Lookup) == "function"),
    apiProbeEntry("Inspect.Unit.Detail", Inspect and Inspect.Unit and type(Inspect.Unit.Detail) == "function"),
    apiProbeEntry("Inspect.Unit.Castbar", Inspect and Inspect.Unit and type(Inspect.Unit.Castbar) == "function"),
    apiProbeEntry("Inspect.Skill", Inspect and type(Inspect.Skill) == "table"),
    apiProbeEntry("Inspect.Currency", Inspect and type(Inspect.Currency) == "table"),
    apiProbeEntry("Inspect.Experience", Inspect and type(Inspect.Experience) == "table"),
    apiProbeEntry("Inspect.Profession", Inspect and type(Inspect.Profession) == "table"),
    apiProbeEntry("Inspect.Crafting", Inspect and type(Inspect.Crafting) == "table"),
    apiProbeEntry("Inspect.Cursor", Inspect and type(Inspect.Cursor) == "function"),
    apiProbeEntry("Inspect.Interaction", Inspect and type(Inspect.Interaction) == "function"),
    apiProbeEntry("Inspect.Tooltip", Inspect and type(Inspect.Tooltip) == "function"),
    apiProbeEntry("Command.Cursor", Command and type(Command.Cursor) == "function"),
    apiProbeEntry("Event.Cursor", Event and type(Event.Cursor) == "table"),
    apiProbeEntry("Event.Interaction", Event and type(Event.Interaction) == "table"),
    apiProbeEntry("Event.Chat", Event and type(Event.Chat) == "table"),
    apiProbeEntry("Event.Chat.Notify", Event and Event.Chat and type(Event.Chat.Notify) == "table"),
    apiProbeEntry("Event.Skill", Event and type(Event.Skill) == "table"),
    apiProbeEntry("Event.Currency", Event and type(Event.Currency) == "table"),
    apiProbeEntry("Event.Experience", Event and type(Event.Experience) == "table"),
    apiProbeEntry("Event.Profession", Event and type(Event.Profession) == "table"),
    apiProbeEntry("Event.Crafting", Event and type(Event.Crafting) == "table"),
    apiProbeEntry("Event.System.Error", Event and Event.System and type(Event.System.Error) == "table"),
    apiProbeEntry("Event.Item.Slot", Event and Event.Item and type(Event.Item.Slot) == "table"),
    apiProbeEntry("Event.Item.Update", Event and Event.Item and type(Event.Item.Update) == "table"),
    apiProbeEntry("Event.Ability.New.Usable.True", Event and Event.Ability and Event.Ability.New and Event.Ability.New.Usable and type(Event.Ability.New.Usable.True) == "table"),
    apiProbeEntry("Event.Ability.New.Usable.False", Event and Event.Ability and Event.Ability.New and Event.Ability.New.Usable and type(Event.Ability.New.Usable.False) == "table"),
    apiProbeEntry("Event.Buff.Add", Event and Event.Buff and type(Event.Buff.Add) == "table"),
    apiProbeEntry("Event.Buff.Change", Event and Event.Buff and type(Event.Buff.Change) == "table"),
    apiProbeEntry("Event.Buff.Remove", Event and Event.Buff and type(Event.Buff.Remove) == "table"),
    apiProbeEntry("Inspect.Console.List", Inspect and Inspect.Console and type(Inspect.Console.List) == "function"),
    apiProbeEntry("Inspect.Console.Detail", Inspect and Inspect.Console and type(Inspect.Console.Detail) == "function"),
    apiProbeEntry("Utility.Item.Slot.Inventory", Utility and Utility.Item and Utility.Item.Slot and type(Utility.Item.Slot.Inventory) == "function"),
    apiProbeEntry("Utility.Item.Slot.Equipment", Utility and Utility.Item and Utility.Item.Slot and type(Utility.Item.Slot.Equipment) == "function"),
    apiProbeEntry("Utility.Item.Slot.Parse", Utility and Utility.Item and Utility.Item.Slot and type(Utility.Item.Slot.Parse) == "function"),
  }
end

local function formatProbeValue(value)
  if value == nil then
    return "nil"
  end

  if type(value) == "table" then
    return "table(" .. tostring(countEntries(value)) .. ")"
  end

  return trimText(tostring(value), 40)
end

local function formatInteractionSummary(interactions)
  if type(interactions) ~= "table" then
    return formatProbeValue(interactions)
  end

  local names = {}
  for name, active in pairs(interactions) do
    if active then
      names[#names + 1] = tostring(name)
    end
  end

  table.sort(names)
  if #names == 0 then
    return "none-active"
  end

  return table.concat(names, ",")
end

local function collectFocusedApiSignalSnapshot()
  local signals = {
    cursor = {
      available = Inspect and type(Inspect.Cursor) == "function",
    },
    tooltip = {
      available = Inspect and type(Inspect.Tooltip) == "function",
    },
    interaction = {
      available = Inspect and type(Inspect.Interaction) == "function",
    },
  }

  if signals.cursor.available then
    local ok, cursorType, held = pcall(Inspect.Cursor)
    signals.cursor.ok = ok == true
    if ok then
      signals.cursor.type = formatProbeValue(cursorType)
      signals.cursor.held = formatProbeValue(held)
    else
      signals.cursor.error = trimText(cursorType, 80)
    end
  end

  if signals.tooltip.available then
    local ok, tooltipType, shown, extra, fourth = pcall(Inspect.Tooltip)
    signals.tooltip.ok = ok == true
    if ok then
      signals.tooltip.type = formatProbeValue(tooltipType)
      signals.tooltip.shown = formatProbeValue(shown)
      signals.tooltip.extra = formatProbeValue(extra)
      signals.tooltip.fourth = formatProbeValue(fourth)
    else
      signals.tooltip.error = trimText(tooltipType, 80)
    end
  end

  if signals.interaction.available then
    local ok, interactions = pcall(Inspect.Interaction)
    signals.interaction.ok = ok == true
    if ok then
      signals.interaction.rawType = type(interactions)
      signals.interaction.summary = formatInteractionSummary(interactions)
      signals.interaction.count = type(interactions) == "table" and countEntries(interactions) or 0
    else
      signals.interaction.error = trimText(interactions, 80)
    end
  end

  return signals
end

local function traceValuePresent(value, absentValue)
  if value == nil then
    return false
  end

  local text = tostring(value)
  return text ~= "nil" and text ~= "?" and text ~= absentValue
end

local function printLiveApiSignals()
  local signals = collectFocusedApiSignalSnapshot()

  if signals.cursor.available then
    Console.Write(
      "  Inspect.Cursor: type=" .. formatProbeValue(signals.cursor.type) .. " held=" .. formatProbeValue(signals.cursor.held),
      "#CCCCCC"
    )
  end

  if signals.tooltip.available then
    Console.Write(
      "  Inspect.Tooltip: type=" .. formatProbeValue(signals.tooltip.type) .. " shown=" .. formatProbeValue(signals.tooltip.shown) .. " extra=" .. formatProbeValue(signals.tooltip.extra) .. " fourth=" .. formatProbeValue(signals.tooltip.fourth),
      "#CCCCCC"
    )
  end

  if signals.interaction.available then
    Console.Write(
      "  Inspect.Interaction: " .. formatProbeValue(signals.interaction.summary),
      "#CCCCCC"
    )
  end
end

local function printCursorSignal()
  local signals = collectFocusedApiSignalSnapshot()
  if not signals.cursor.available then
    Console.Write("Inspect.Cursor unavailable.", "#FFAA44")
    return
  end

  Console.Write(
    "Inspect.Cursor type=" .. formatProbeValue(signals.cursor.type) .. " held=" .. formatProbeValue(signals.cursor.held),
    "#66CCFF"
  )
end

local function printTooltipSignal()
  local signals = collectFocusedApiSignalSnapshot()
  if not signals.tooltip.available then
    Console.Write("Inspect.Tooltip unavailable.", "#FFAA44")
    return
  end

  Console.Write(
    "Inspect.Tooltip type=" .. formatProbeValue(signals.tooltip.type) .. " shown=" .. formatProbeValue(signals.tooltip.shown) .. " extra=" .. formatProbeValue(signals.tooltip.extra) .. " fourth=" .. formatProbeValue(signals.tooltip.fourth),
    "#66CCFF"
  )
end

local function printInteractionSignal()
  local signals = collectFocusedApiSignalSnapshot()
  if not signals.interaction.available then
    Console.Write("Inspect.Interaction unavailable.", "#FFAA44")
    return
  end

  Console.Write("Inspect.Interaction " .. formatProbeValue(signals.interaction.summary), "#66CCFF")
end

local function collectTableKeys(root, limit)
  local keys = {}
  if type(root) ~= "table" then
    return keys
  end

  for key, value in pairs(root) do
    keys[#keys + 1] = {
      name = tostring(key),
      valueType = type(value),
    }
  end

  table.sort(keys, function(left, right)
    return tostring(left.name) < tostring(right.name)
  end)

  local maxCount = math.min(#keys, limit or 24)
  local trimmed = {}
  for index = 1, maxCount do
    trimmed[index] = keys[index]
  end

  return trimmed
end

local function printTableKeys(title, root, limit)
  local keys = collectTableKeys(root, limit)
  Console.Write(title .. " keys=" .. tostring(#keys), "#FFFF88")

  if #keys == 0 then
    Console.Write("  none or unavailable", "#FFAA44")
    return
  end

  for _, entry in ipairs(keys) do
    Console.Write("  " .. tostring(entry.name) .. "=" .. tostring(entry.valueType), "#CCCCCC")
  end
end

local function formatCompactTableKeys(root, limit)
  local keys = collectTableKeys(root, limit or 6)
  if #keys == 0 then
    return "none"
  end

  local parts = {}
  for _, entry in ipairs(keys) do
    parts[#parts + 1] = tostring(entry.name) .. ":" .. tostring(entry.valueType)
  end
  return table.concat(parts, ",")
end

local function formatCompactAvailability(entries)
  local parts = {}
  for _, entry in ipairs(entries) do
    parts[#parts + 1] = tostring(entry[1]) .. "=" .. tostring(entry[2] and true or false)
  end
  return table.concat(parts, " ")
end

local function buildObservationSnapshot(snapshot)
  snapshot = type(snapshot) == "table" and snapshot or {}

  local player = type(snapshot.player) == "table" and snapshot.player or {}
  local inventory = type(snapshot.inventory) == "table" and snapshot.inventory or {}
  local fishing = type(snapshot.fishing) == "table" and snapshot.fishing or {}
  local castbar = type(snapshot.castbar) == "table" and snapshot.castbar or {}
  local notes = {}

  local inGame = player.available == true
  if not inGame then
    addObservationNote(notes, "player native unit is unavailable")
  end

  local inCombat = player.combat == true
  if inCombat then
    addObservationNote(notes, "player is in combat")
  end

  if snapshot.secureMode == true then
    addObservationNote(notes, "Rift secure mode is active")
  end

  local inventoryFull = true
  if type(inventory.estimatedFreeSlots) == "number" then
    inventoryFull = inventory.estimatedFreeSlots <= 0
  else
    addObservationNote(notes, "inventory free slots are unknown; treating inventory as full")
  end

  local poleCandidate = fishing.equippedPole or fishing.inventoryPole
  if type(poleCandidate) ~= "table" then
    addObservationNote(notes, "no native fishing pole candidate is visible")
  end

  local baitAvailable = hasEntries(fishing.baitCandidates) or hasEntries(fishing.lureAbilityCandidates)
  if not baitAvailable then
    addObservationNote(notes, "no native bait/lure candidate matched inventory or usable ability scans")
  end

  local trackFishVisible = type(fishing.trackFishBuff) == "table"
  if not trackFishVisible then
    addObservationNote(notes, "Track Fish buff was not detected")
  end

  local lineCast = castbar.active == true and containsText(castbar.abilityName, "fish")
  if castbar.active == true and not lineCast then
    addObservationNote(notes, "a non-fishing castbar is active")
  end

  local nearWater = false
  addObservationNote(notes, "near_water is not confirmed by native addon APIs yet")

  local canCast = inGame
    and not inCombat
    and snapshot.secureMode ~= true
    and not inventoryFull
    and type(poleCandidate) == "table"
    and baitAvailable
    and nearWater

  local confidence = 0.2
  if inGame then
    confidence = confidence + 0.15
  end
  if type(poleCandidate) == "table" then
    confidence = confidence + 0.10
  end
  if type(inventory.estimatedFreeSlots) == "number" then
    confidence = confidence + 0.10
  end
  if trackFishVisible then
    confidence = confidence + 0.05
  end
  if canCast then
    confidence = 0.85
  elseif not nearWater or not baitAvailable then
    confidence = math.min(confidence, 0.45)
  end

  return {
    timestamp = toNumber(snapshot.capturedAt) or now(),
    in_game = inGame,
    near_water = nearWater,
    in_combat = inCombat,
    inventory_full = inventoryFull,
    bait_available = baitAvailable,
    line_cast = lineCast,
    bobber_visible = false,
    bite_detected = false,
    loot_window_open = false,
    skill_up_ready = false,
    durability_low = false,
    can_cast = canCast,
    stuck_for_seconds = 0,
    confidence = confidence,
    notes = notes,
  }
end

local function ensureTrace()
  ensureState()
  state.trace = type(state.trace) == "table" and state.trace or {}
  state.trace.samples = type(state.trace.samples) == "table" and state.trace.samples or {}
  state.trace.active = state.trace.active == true
  state.trace.maxSamples = toNumber(state.trace.maxSamples) or MAX_TRACE_SAMPLES
  return state.trace
end

local function trimTraceSamples(trace)
  local maxSamples = math.max(1, math.min(MAX_TRACE_SAMPLES, toNumber(trace.maxSamples) or MAX_TRACE_SAMPLES))
  while #trace.samples > maxSamples do
    table.remove(trace.samples, 1)
  end
end

local function recordTraceSample(snapshot, observation)
  if state == nil or type(state.trace) ~= "table" or state.trace.active ~= true then
    return
  end

  local trace = ensureTrace()
  local player = type(snapshot.player) == "table" and snapshot.player or {}
  local inventory = type(snapshot.inventory) == "table" and snapshot.inventory or {}
  local fishing = type(snapshot.fishing) == "table" and snapshot.fishing or {}
  local castbar = type(snapshot.castbar) == "table" and snapshot.castbar or {}
  local pole = fishing.equippedPole or fishing.inventoryPole
  local apiSignals = collectFocusedApiSignalSnapshot()
  local cursor = apiSignals.cursor or {}
  local tooltip = apiSignals.tooltip or {}
  local interaction = apiSignals.interaction or {}

  trace.samples[#trace.samples + 1] = {
    capturedAt = snapshot.capturedAt,
    reason = snapshot.reason,
    playerAvailable = player.available == true,
    zone = toString(player.zone or player.locationName),
    combat = player.combat == true,
    secure = snapshot.secureMode == true,
    castbarActive = castbar.active == true,
    castbarAbility = toString(castbar.abilityName),
    lineCast = observation.line_cast == true,
    canCast = observation.can_cast == true,
    confidence = toNumber(observation.confidence) or 0,
    inventoryFreeSlots = inventory.estimatedFreeSlots,
    pole = type(pole) == "table" and (pole.matchText or buildMatchText(pole)) or nil,
    trackFish = type(fishing.trackFishBuff) == "table",
    cursorType = cursor.type,
    cursorHeld = cursor.held,
    tooltipType = tooltip.type,
    tooltipShown = tooltip.shown,
    tooltipExtra = tooltip.extra,
    tooltipFourth = tooltip.fourth,
    interactionSummary = interaction.summary,
  }

  trace.lastCapturedAt = snapshot.capturedAt
  trace.lastReason = snapshot.reason
  trimTraceSamples(trace)
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
  local observation = buildObservationSnapshot(snapshot)
  state.currentObservation = observation
  recordTraceSample(snapshot, observation)
  state.session.lastCapturedAt = snapshot.capturedAt
  state.session.lastReason = snapshot.reason
  AutoFish_State = state

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

  Console.Write(
    string.format(
      "abilityCandidates=%s usableLureAbilities=%s abilityScan=%s",
      tostring(type(snapshot.fishing.abilityCandidates) == "table" and #snapshot.fishing.abilityCandidates or 0),
      tostring(type(snapshot.fishing.lureAbilityCandidates) == "table" and #snapshot.fishing.lureAbilityCandidates or 0),
      tostring(snapshot.fishing.abilityScanError or "ok")),
    "#CCCCCC")

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

local function buildInventoryProofSnapshot(label)
  local inventorySpecifier = Utility and Utility.Item and Utility.Item.Slot and Utility.Item.Slot.Inventory and safeCall(Utility.Item.Slot.Inventory) or nil
  local entries = collectItemEntries(inventorySpecifier, "inventory")
  local bagSummaries, knownContainerSlots, knownUsedSlots, estimatedFreeSlots = collectBagSummaries()
  local aggregates = {}

  for _, entry in ipairs(entries) do
    local key = entry.id or entry.itemId or entry.name or entry.slot or "unknown"
    local aggregate = aggregates[key]
    if type(aggregate) ~= "table" then
      aggregate = {
        key = key,
        id = entry.id,
        itemId = entry.itemId,
        name = entry.name,
        category = entry.category,
        typeName = entry.typeName,
        quantity = 0,
        stacks = 0,
        slots = {},
      }
      aggregates[key] = aggregate
    end

    aggregate.quantity = aggregate.quantity + (toNumber(entry.stack) or 1)
    aggregate.stacks = aggregate.stacks + 1
    aggregate.slots[#aggregate.slots + 1] = entry.slot
  end

  return {
    label = label,
    capturedAt = now(),
    itemCount = #entries,
    knownContainerSlots = knownContainerSlots,
    knownUsedSlots = knownUsedSlots,
    estimatedFreeSlots = estimatedFreeSlots,
    bagSummaries = bagSummaries,
    entries = entries,
    aggregates = aggregates,
  }
end

local function inventoryProofDisplayName(entry)
  if type(entry) ~= "table" then
    return "unknown"
  end

  return trimText(entry.name or entry.key or entry.id or entry.itemId or "unknown", 46)
end

local function computeInventoryProofDiff(before, after)
  local changes = {}
  local seen = {}
  local beforeAggregates = type(before) == "table" and type(before.aggregates) == "table" and before.aggregates or {}
  local afterAggregates = type(after) == "table" and type(after.aggregates) == "table" and after.aggregates or {}

  for key, afterEntry in pairs(afterAggregates) do
    seen[key] = true
    local beforeEntry = beforeAggregates[key] or {}
    local delta = (toNumber(afterEntry.quantity) or 0) - (toNumber(beforeEntry.quantity) or 0)
    if delta ~= 0 then
      changes[#changes + 1] = {
        key = key,
        name = afterEntry.name or beforeEntry.name,
        beforeQuantity = toNumber(beforeEntry.quantity) or 0,
        afterQuantity = toNumber(afterEntry.quantity) or 0,
        delta = delta,
      }
    end
  end

  for key, beforeEntry in pairs(beforeAggregates) do
    if not seen[key] then
      local beforeQuantity = toNumber(beforeEntry.quantity) or 0
      if beforeQuantity ~= 0 then
        changes[#changes + 1] = {
          key = key,
          name = beforeEntry.name,
          beforeQuantity = beforeQuantity,
          afterQuantity = 0,
          delta = -beforeQuantity,
        }
      end
    end
  end

  table.sort(changes, function(left, right)
    local leftAbs = math.abs(toNumber(left.delta) or 0)
    local rightAbs = math.abs(toNumber(right.delta) or 0)
    if leftAbs ~= rightAbs then
      return leftAbs > rightAbs
    end

    return lower(left.name or left.key) < lower(right.name or right.key)
  end)

  return changes
end

local function inventoryProofSlotIdentity(entry)
  if type(entry) ~= "table" then
    return ""
  end

  return table.concat({
    tostring(entry.id or ""),
    tostring(entry.itemId or ""),
    tostring(entry.name or ""),
    tostring(entry.stack or ""),
  }, "|")
end

local function buildInventoryProofSlotMap(snapshot)
  local map = {}
  local entries = type(snapshot) == "table" and type(snapshot.entries) == "table" and snapshot.entries or {}

  for _, entry in ipairs(entries) do
    if type(entry) == "table" and entry.slot ~= nil then
      map[tostring(entry.slot)] = entry
    end
  end

  return map
end

local function computeInventoryProofSlotChanges(before, after)
  local changes = {}
  local seen = {}
  local beforeSlots = buildInventoryProofSlotMap(before)
  local afterSlots = buildInventoryProofSlotMap(after)

  for slot, afterEntry in pairs(afterSlots) do
    seen[slot] = true
    local beforeEntry = beforeSlots[slot]
    if type(beforeEntry) ~= "table" then
      changes[#changes + 1] = {
        slot = slot,
        kind = "added",
        afterName = afterEntry.name,
        afterId = afterEntry.id or afterEntry.itemId,
        afterStack = afterEntry.stack,
      }
    elseif inventoryProofSlotIdentity(beforeEntry) ~= inventoryProofSlotIdentity(afterEntry) then
      changes[#changes + 1] = {
        slot = slot,
        kind = "changed",
        beforeName = beforeEntry.name,
        beforeId = beforeEntry.id or beforeEntry.itemId,
        beforeStack = beforeEntry.stack,
        afterName = afterEntry.name,
        afterId = afterEntry.id or afterEntry.itemId,
        afterStack = afterEntry.stack,
      }
    end
  end

  for slot, beforeEntry in pairs(beforeSlots) do
    if not seen[slot] then
      changes[#changes + 1] = {
        slot = slot,
        kind = "removed",
        beforeName = beforeEntry.name,
        beforeId = beforeEntry.id or beforeEntry.itemId,
        beforeStack = beforeEntry.stack,
      }
    end
  end

  table.sort(changes, function(left, right)
    return tostring(left.slot or "") < tostring(right.slot or "")
  end)

  return changes
end

local function printInventoryProofSnapshot(label, snapshot)
  Console.Write(
    string.format(
      "%s inventory proof: items=%s knownSlots=%s used=%s estFree=%s",
      tostring(label),
      tostring(snapshot.itemCount or 0),
      tostring(snapshot.knownContainerSlots or 0),
      tostring(snapshot.knownUsedSlots or 0),
      tostring(snapshot.estimatedFreeSlots ~= nil and snapshot.estimatedFreeSlots or "?")),
    "#66CCFF")
end

function AutoFishLive.PrintInventoryProof(argsText)
  ensureState()
  state.inventoryProof = type(state.inventoryProof) == "table" and state.inventoryProof or {}

  local subcommand = string.match(argsText or "", "^%S+%s+(%S+)")
  if subcommand then
    subcommand = string.lower(subcommand)
  else
    subcommand = "status"
  end

  if subcommand == "before" or subcommand == "start" then
    state.inventoryProof.before = buildInventoryProofSnapshot("before")
    state.inventoryProof.after = nil
    state.inventoryProof.changes = nil
    AutoFish_State = state
    printInventoryProofSnapshot("before", state.inventoryProof.before)
    Console.Write("Now perform one manual cast/catch, then run /autofish invproof after.", "#CCCCCC")
    return
  end

  if subcommand == "after" or subcommand == "stop" then
    if type(state.inventoryProof.before) ~= "table" then
      Console.Write("No before snapshot. Run /autofish invproof before first.", "#FFAA44")
      return
    end

    state.inventoryProof.after = buildInventoryProofSnapshot("after")
    state.inventoryProof.changes = computeInventoryProofDiff(state.inventoryProof.before, state.inventoryProof.after)
    state.inventoryProof.slotChanges = computeInventoryProofSlotChanges(state.inventoryProof.before, state.inventoryProof.after)
    AutoFish_State = state
    printInventoryProofSnapshot("after", state.inventoryProof.after)
    AutoFishLive.PrintInventoryProof("invproof diff")
    return
  end

  if subcommand == "clear" then
    state.inventoryProof = {}
    AutoFish_State = state
    Console.Write("Inventory proof snapshots cleared.", "#00CC88")
    return
  end

  if subcommand ~= "status" and subcommand ~= "diff" then
    Console.Write("Unknown inventory proof command. Use /autofish invproof before|after|diff|status|clear.", "#FF4444")
    return
  end

  local proof = state.inventoryProof or {}
  local before = proof.before
  local after = proof.after
  if type(before) ~= "table" then
    Console.Write("Inventory proof has no before snapshot. Use /autofish invproof before.", "#FFAA44")
    return
  end

  printInventoryProofSnapshot("before", before)

  if type(after) ~= "table" then
    Console.Write("No after snapshot yet. Use /autofish invproof after one manual catch/loot attempt.", "#FFAA44")
    return
  end

  printInventoryProofSnapshot("after", after)

  local changes = type(proof.changes) == "table" and proof.changes or computeInventoryProofDiff(before, after)
  proof.changes = changes
  local slotChanges = type(proof.slotChanges) == "table" and proof.slotChanges or computeInventoryProofSlotChanges(before, after)
  proof.slotChanges = slotChanges
  AutoFish_State = state

  if #changes == 0 then
    if #slotChanges == 0 then
      Console.Write("Inventory proof diff: no item quantity or raw slot changes detected.", "#FFAA44")
      return
    end

    Console.Write("Inventory proof diff: no item quantity changes; raw slot changes detected:", "#FFAA44")
    for index = 1, math.min(#slotChanges, 10) do
      local change = slotChanges[index]
      local beforeText = trimText(change.beforeName or change.beforeId or "-", 28)
      local afterText = trimText(change.afterName or change.afterId or "-", 28)
      Console.Write(
        string.format(
          "  %s. slot=%s %s %s(x%s) -> %s(x%s)",
          tostring(index),
          tostring(change.slot or "?"),
          tostring(change.kind or "changed"),
          beforeText,
          tostring(change.beforeStack or "-"),
          afterText,
          tostring(change.afterStack or "-")),
        "#CCCCCC")
    end

    if #slotChanges > 10 then
      Console.Write("  ... " .. tostring(#slotChanges - 10) .. " more raw slot changes omitted.", "#CCCCCC")
    end
    return
  end

  Console.Write("Inventory proof diff:", "#FFFF88")
  for index = 1, math.min(#changes, 10) do
    local change = changes[index]
    Console.Write(
      string.format(
        "  %s. %+d %s before=%s after=%s",
        tostring(index),
        toNumber(change.delta) or 0,
        inventoryProofDisplayName(change),
        tostring(change.beforeQuantity or 0),
        tostring(change.afterQuantity or 0)),
      change.delta and change.delta > 0 and "#00CC88" or "#FFAA44")
  end

  if #changes > 10 then
    Console.Write("  ... " .. tostring(#changes - 10) .. " more changes omitted.", "#CCCCCC")
  end
end

function AutoFishLive.PrintPoleCandidates()
  local snapshot = AutoFishLive.Refresh("slash.pole", true)
  printCandidateList("Fishing pole candidates:", snapshot.fishing.poleCandidates, "  No fishing-pole candidates matched equipped or carried items.")
end

function AutoFishLive.PrintAbilityCandidates(argsText)
  AutoFishLive.Refresh("slash.abilities", true)

  local filter = string.match(argsText or "", "^%S+%s+(%S+)")
  local keywords = FISHING_ABILITY_KEYWORDS
  if filter ~= nil and filter ~= "" then
    keywords = { filter }
  end

  local candidates, errorText = nil, nil
  if filter ~= nil and filter ~= "" then
    candidates, errorText = collectAbilityMatches(keywords, MAX_MATCHES)
  else
    candidates, errorText = getFishingAbilityCandidates(true)
  end
  state.lastAbilityCandidates = candidates
  state.lastAbilityScanError = errorText

  Console.Write("Fishing-related ability candidates:", "#FFFF88")

  if errorText then
    Console.Write("  " .. tostring(errorText), "#FF4444")
    return
  end

  if type(candidates) ~= "table" or #candidates == 0 then
    Console.Write("  No fishing-related ability candidates matched Inspect.Ability.New.", "#FFAA44")
    return
  end

  for index, candidate in ipairs(candidates) do
    Console.Write(
      string.format(
        "  %s. %s id=%s unusable=%s range=%s cd=%s cast=%s",
        tostring(index),
        trimText(candidate.name or "unknown", 32),
        tostring(candidate.id or "?"),
        tostring(candidate.unusable and true or false),
        tostring(candidate.outOfRange and "out" or "ok"),
        tostring(candidate.currentCooldownRemaining or 0),
        tostring(candidate.castingTime or 0)),
      "#CCCCCC")
  end
end

function AutoFishLive.PrintApiProbe()
  AutoFishLive.Refresh("slash.api", true)

  local probe = collectApiProbe()
  state.lastApiProbe = probe

  Console.Write("API probe:", "#FFFF88")

  for _, entry in ipairs(probe) do
    Console.Write(
      string.format(
        "  %s=%s",
        tostring(entry.name or "?"),
        tostring(entry.available and true or false)),
      entry.available and "#CCCCCC" or "#FFAA44")
  end

  Console.Write("Live read-only API signals:", "#FFFF88")
  printLiveApiSignals()
end

function AutoFishLive.PrintApiTables()
  AutoFishLive.Refresh("slash.apis", true)

  printTableKeys("Command", Command, 32)
  printTableKeys("Command.Ability", Command and Command.Ability, 32)
  printTableKeys("Command.Item", Command and Command.Item, 32)
  printTableKeys("Command.Macro", Command and Command.Macro, 32)
  printTableKeys("Inspect.Action", Inspect and Inspect.Action, 32)
  printTableKeys("Inspect.Ability", Inspect and Inspect.Ability, 32)
  printTableKeys("Inspect.Ability.New", Inspect and Inspect.Ability and Inspect.Ability.New, 32)
  printTableKeys("Inspect.Buff", Inspect and Inspect.Buff, 32)
  printTableKeys("Inspect.Item", Inspect and Inspect.Item, 32)
  printTableKeys("Inspect.Unit", Inspect and Inspect.Unit, 32)
  printTableKeys("Inspect.Skill", Inspect and Inspect.Skill, 32)
  printTableKeys("Inspect.Currency", Inspect and Inspect.Currency, 32)
  printTableKeys("Inspect.Experience", Inspect and Inspect.Experience, 32)
  printTableKeys("Inspect.Profession", Inspect and Inspect.Profession, 32)
  printTableKeys("Inspect.Crafting", Inspect and Inspect.Crafting, 32)
  printTableKeys("Inspect.Macro", Inspect and Inspect.Macro, 32)
  printTableKeys("Utility.Item", Utility and Utility.Item, 32)
  printTableKeys("Utility.Item.Slot", Utility and Utility.Item and Utility.Item.Slot, 32)
end

function AutoFishLive.PrintApiSignals()
  AutoFishLive.Refresh("slash.signals", true)

  Console.Write("Focused live API signals:", "#FFFF88")
  printCursorSignal()
  printTooltipSignal()
  printInteractionSignal()
end

function AutoFishLive.PrintApiEvents()
  AutoFishLive.Refresh("slash.events", true)

  printTableKeys("Event.Cursor", Event and Event.Cursor, 24)
  printTableKeys("Event.Interaction", Event and Event.Interaction, 24)
  printTableKeys("Event.Chat", Event and Event.Chat, 32)
  printTableKeys("Event.System", Event and Event.System, 32)
  printTableKeys("Event.Item", Event and Event.Item, 32)
  printTableKeys("Event.Ability.New", Event and Event.Ability and Event.Ability.New, 32)
  printTableKeys("Event.Buff", Event and Event.Buff, 32)
  printTableKeys("Event.Skill", Event and Event.Skill, 32)
  printTableKeys("Event.Currency", Event and Event.Currency, 32)
  printTableKeys("Event.Experience", Event and Event.Experience, 32)
  printTableKeys("Event.Profession", Event and Event.Profession, 32)
  printTableKeys("Event.Crafting", Event and Event.Crafting, 32)
  printTableKeys("Inspect.Console", Inspect and Inspect.Console, 24)
end

function AutoFishLive.PrintApiCompact()
  AutoFishLive.Refresh("slash.apicompact", true)

  Console.Write("API compact proof:", "#FFFF88")
  Console.Write(
    "  inventory " .. formatCompactAvailability({
      { "Item.List", Inspect and Inspect.Item and type(Inspect.Item.List) == "function" },
      { "Item.Detail", Inspect and Inspect.Item and type(Inspect.Item.Detail) == "function" },
      { "Slot.Inventory", Utility and Utility.Item and Utility.Item.Slot and type(Utility.Item.Slot.Inventory) == "function" },
      { "Event.Item.Slot", Event and Event.Item and type(Event.Item.Slot) == "table" },
      { "Event.Item.Update", Event and Event.Item and type(Event.Item.Update) == "table" },
    }),
    "#CCCCCC")
  Console.Write(
    "  chat/cursor " .. formatCompactAvailability({
      { "Event.Chat.Notify", Event and Event.Chat and type(Event.Chat.Notify) == "table" },
      { "Inspect.Cursor", Inspect and type(Inspect.Cursor) == "function" },
      { "Inspect.Tooltip", Inspect and type(Inspect.Tooltip) == "function" },
      { "Inspect.Interaction", Inspect and type(Inspect.Interaction) == "function" },
    }),
    "#CCCCCC")
  Console.Write(
    "  inspect progression " .. formatCompactAvailability({
      { "Skill", Inspect and type(Inspect.Skill) == "table" },
      { "Currency", Inspect and type(Inspect.Currency) == "table" },
      { "Experience", Inspect and type(Inspect.Experience) == "table" },
      { "Profession", Inspect and type(Inspect.Profession) == "table" },
      { "Crafting", Inspect and type(Inspect.Crafting) == "table" },
    }),
    "#CCCCCC")
  Console.Write(
    "  event progression " .. formatCompactAvailability({
      { "Skill", Event and type(Event.Skill) == "table" },
      { "Currency", Event and type(Event.Currency) == "table" },
      { "Experience", Event and type(Event.Experience) == "table" },
      { "Profession", Event and type(Event.Profession) == "table" },
      { "Crafting", Event and type(Event.Crafting) == "table" },
    }),
    "#CCCCCC")
  Console.Write("  Event.Chat keys=" .. formatCompactTableKeys(Event and Event.Chat, 5), "#CCCCCC")
  Console.Write("  Event.Item keys=" .. formatCompactTableKeys(Event and Event.Item, 5), "#CCCCCC")
  Console.Write("  Event.Currency keys=" .. formatCompactTableKeys(Event and Event.Currency, 5), "#CCCCCC")
  Console.Write("  Event.Experience keys=" .. formatCompactTableKeys(Event and Event.Experience, 5), "#CCCCCC")
  Console.Write("  Inspect.Skill keys=" .. formatCompactTableKeys(Inspect and Inspect.Skill, 5), "#CCCCCC")
  Console.Write("  Inspect.Currency keys=" .. formatCompactTableKeys(Inspect and Inspect.Currency, 5), "#CCCCCC")
end

function AutoFishLive.PrintObservation()
  local snapshot = AutoFishLive.Refresh("slash.observation", true)
  local observation = state.currentObservation or buildObservationSnapshot(snapshot)

  Console.Write(
    string.format(
      "observation in_game=%s near_water=%s inventory_full=%s bait_available=%s line_cast=%s can_cast=%s confidence=%.2f",
      tostring(observation.in_game and true or false),
      tostring(observation.near_water and true or false),
      tostring(observation.inventory_full and true or false),
      tostring(observation.bait_available and true or false),
      tostring(observation.line_cast and true or false),
      tostring(observation.can_cast and true or false),
      toNumber(observation.confidence) or 0),
    "#66CCFF")

  Console.Write(
    string.format(
      "observation combat=%s bobber=%s bite=%s loot=%s stuck=%s",
      tostring(observation.in_combat and true or false),
      tostring(observation.bobber_visible and true or false),
      tostring(observation.bite_detected and true or false),
      tostring(observation.loot_window_open and true or false),
      tostring(observation.stuck_for_seconds or 0)),
    "#CCCCCC")

  if type(observation.notes) == "table" then
    for _, note in ipairs(observation.notes) do
      Console.Write("  note: " .. tostring(note), "#FFAA44")
    end
  end
end

function AutoFishLive.PrintTrace(argsText)
  local subcommand = string.match(argsText or "", "^%S+%s+(%S+)")
  if subcommand then
    subcommand = string.lower(subcommand)
  else
    subcommand = "status"
  end

  local trace = ensureTrace()

  if subcommand == "start" then
    trace.active = true
    trace.startedAt = now()
    trace.samples = {}
    AutoFishLive.Refresh("trace.start", true)
    Console.Write("Trace started. Manually perform one action, then use /autofish trace status or /autofish trace stop.", "#00CC88")
    return
  end

  if subcommand == "stop" then
    AutoFishLive.Refresh("trace.stop", true)
    trace.active = false
    trace.stoppedAt = now()
    Console.Write("Trace stopped. samples=" .. tostring(#trace.samples), "#00CC88")
    return
  end

  if subcommand == "clear" then
    trace.active = false
    trace.samples = {}
    trace.startedAt = nil
    trace.stoppedAt = nil
    trace.lastCapturedAt = nil
    trace.lastReason = nil
    Console.Write("Trace cleared.", "#00CC88")
    return
  end

  if subcommand ~= "status" then
    Console.Write("Unknown trace command. Use /autofish trace start|status|stop|clear.", "#FF4444")
    return
  end

  AutoFishLive.Refresh("trace.status", true)
  local last = trace.samples[#trace.samples] or {}
  local cursorNonNil = 0
  local tooltipNonNil = 0
  local interactionActive = 0
  for _, sample in ipairs(trace.samples) do
    if traceValuePresent(sample.cursorType) or traceValuePresent(sample.cursorHeld) then
      cursorNonNil = cursorNonNil + 1
    end
    if traceValuePresent(sample.tooltipType) or traceValuePresent(sample.tooltipShown) or traceValuePresent(sample.tooltipExtra) or traceValuePresent(sample.tooltipFourth) then
      tooltipNonNil = tooltipNonNil + 1
    end
    if traceValuePresent(sample.interactionSummary, "none-active") then
      interactionActive = interactionActive + 1
    end
  end
  Console.Write(
    string.format(
      "trace active=%s samples=%s lastReason=%s",
      tostring(trace.active and true or false),
      tostring(#trace.samples),
      tostring(trace.lastReason or "?")),
    "#66CCFF")
  Console.Write(
    string.format(
      "trace last castbar=%s ability=%s line_cast=%s can_cast=%s confidence=%.2f free=%s",
      tostring(last.castbarActive and true or false),
      tostring(last.castbarAbility or "?"),
      tostring(last.lineCast and true or false),
      tostring(last.canCast and true or false),
      toNumber(last.confidence) or 0,
      tostring(last.inventoryFreeSlots ~= nil and last.inventoryFreeSlots or "?")),
    "#CCCCCC")
  Console.Write(
    string.format(
      "trace last api cursor=%s held=%s tooltip=%s shown=%s extra=%s interact=%s",
      tostring(last.cursorType or "?"),
      tostring(last.cursorHeld or "?"),
      tostring(last.tooltipType or "?"),
      tostring(last.tooltipShown or "?"),
      tostring(last.tooltipExtra or "?"),
      tostring(last.interactionSummary or "?")),
    "#CCCCCC")
  Console.Write(
    string.format(
      "trace api counts cursor_non_nil=%s tooltip_non_nil=%s interaction_active=%s",
      tostring(cursorNonNil),
      tostring(tooltipNonNil),
      tostring(interactionActive)),
    "#CCCCCC")

  local first = math.max(1, #trace.samples - 2)
  for index = first, #trace.samples do
    local sample = trace.samples[index] or {}
    Console.Write(
      string.format(
        "trace sample %s reason=%s cursor=%s tooltip=%s interact=%s",
        tostring(index),
        tostring(sample.reason or "?"),
        tostring(sample.cursorType or "?"),
        tostring(sample.tooltipType or "?"),
        tostring(sample.interactionSummary or "?")),
      "#888888")
  end
end

function AutoFishLive.PrintCoords()
  local snapshot = AutoFishLive.Refresh("slash.coords", true)
  local player = snapshot.player or {}

  if not player.available then
    Console.Write("Player unit is not ready yet. Coordinates unavailable.", "#FFAA44")
    return
  end

  local coord = player.coord or {}
  Console.Write(
    string.format(
      "coords x=%s y=%s z=%s playerUnit=%s",
      formatCoordValue(coord.x),
      formatCoordValue(coord.y),
      formatCoordValue(coord.z),
      tostring(player.playerUnit or "?")),
    "#00CC88")
  Console.Write("source=Inspect.Unit.Lookup(\"player\") -> Inspect.Unit.Detail(playerUnit).coordX/Y/Z", "#CCCCCC")
  Console.Write("usage=cross-check ChromaLink and facing-delta; not native actor-facing/yaw", "#FFAA44")
end

function AutoFishLive.PrintHelp()
  Console.Write("Commands:", "#FFFF88")
  Console.Write("  /autofish status    - show player, zone, secure state, and inventory summary", "#CCCCCC")
  Console.Write("  /autofish coords    - show player coordX/coordY/coordZ from Inspect.Unit.Detail", "#CCCCCC")
  Console.Write("  /autofish bags      - inspect bag containers and used/free slot counts", "#CCCCCC")
  Console.Write("  /autofish inventory - inspect bait/lure-related inventory candidates", "#CCCCCC")
  Console.Write("  /autofish invproof  - before/after/diff proof for inventory catch deltas", "#CCCCCC")
  Console.Write("  /autofish pole      - search equipped and carried fishing-pole candidates", "#CCCCCC")
  Console.Write("  /autofish abilities - search fishing-related native abilities", "#CCCCCC")
  Console.Write("  /autofish api       - show native API availability relevant to fishing probes", "#CCCCCC")
  Console.Write("  /autofish apicompact - compact API proof for screenshot capture", "#CCCCCC")
  Console.Write("  /autofish apis      - list use/action-related API table keys", "#CCCCCC")
  Console.Write("  /autofish signals   - show cursor, tooltip, and interaction API values", "#CCCCCC")
  Console.Write("  /autofish events    - list useful event table keys for feedback probes", "#CCCCCC")
  Console.Write("  /autofish observe   - show fail-closed bridge observation mapping", "#CCCCCC")
  Console.Write("  /autofish trace     - start/status/stop a bounded manual one-cast/API trace", "#CCCCCC")
  Console.Write("  /autofish snapshot  - refresh the saved snapshot without extra output", "#CCCCCC")
  Console.Write("  /autofish help      - show this help", "#CCCCCC")
end

function AutoFishLive.OnSlashCommand(handle, args)
  local argsText = args
  if argsText == nil and type(handle) == "string" then
    argsText = handle
  end

  local command = string.match(argsText or "", "^(%S+)")
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

  if command == "coords" or command == "coord" or command == "position" or command == "pos" then
    AutoFishLive.PrintCoords()
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

  if command == "invproof" or command == "inventoryproof" then
    AutoFishLive.PrintInventoryProof(argsText)
    return
  end

  if command == "pole" then
    AutoFishLive.PrintPoleCandidates()
    return
  end

  if command == "abilities" or command == "ability" then
    AutoFishLive.PrintAbilityCandidates(argsText)
    return
  end

  if command == "apicompact" or command == "compactapi" then
    AutoFishLive.PrintApiCompact()
    return
  end

  if command == "api" or command == "apis" or command == "probe" then
    if command == "apis" then
      AutoFishLive.PrintApiTables()
    else
      AutoFishLive.PrintApiProbe()
    end
    return
  end

  if command == "signals" or command == "cursor" or command == "tooltip" or command == "interaction" then
    AutoFishLive.PrintApiSignals()
    return
  end

  if command == "events" then
    AutoFishLive.PrintApiEvents()
    return
  end

  if command == "observe" or command == "observation" then
    AutoFishLive.PrintObservation()
    return
  end

  if command == "trace" then
    AutoFishLive.PrintTrace(argsText)
    return
  end

  if command == "snapshot" then
    AutoFishLive.Refresh("slash.snapshot", true)
    Console.Write("Snapshot refreshed.", "#00CC88")
    return
  end

  Console.Write("Unknown command. Use /autofish help.", "#FF4444")
end

local function resolveAddonArgument(first, second)
  if second ~= nil then
    return second
  end

  return first
end

function AutoFishLive.OnSavedVariablesLoad(handle, addon)
  addon = resolveAddonArgument(handle, addon)
  if addon ~= addonIdentifier then
    return
  end

  ensureState()
end

function AutoFishLive.OnSavedVariablesSave(handle, addon)
  addon = resolveAddonArgument(handle, addon)
  if addon ~= addonIdentifier then
    return
  end

  ensureState()
  AutoFishLive.Refresh("save-begin", false)
  AutoFish_State = state
end

function AutoFishLive.OnStartup(handle, addon)
  addon = resolveAddonArgument(handle, addon)
  if addon ~= nil and addon ~= addonIdentifier then
    return
  end

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
    return false
  end

  if Command and Command.Event and Command.Event.Attach then
    Command.Event.Attach(eventTable, handler, label)
    return true
  end

  table.insert(eventTable, { handler, addonIdentifier, label })
  return true
end

local slashEvent = Command and Command.Slash and Command.Slash.Register and Command.Slash.Register("autofish")
attach(slashEvent, AutoFishLive.OnSlashCommand, "AutoFish slash command")

local addonEvents = Event and Event.Addon
local savedVariableEvents = addonEvents and addonEvents.SavedVariables
local savedVariableLoadEvent = savedVariableEvents and savedVariableEvents.Load and savedVariableEvents.Load.End
local savedVariableSaveEvent = savedVariableEvents and savedVariableEvents.Save and savedVariableEvents.Save.Begin
local addonLoadEvent = addonEvents and addonEvents.Load and addonEvents.Load.End

if not addonLoadEvent and addonEvents and addonEvents.Startup then
  addonLoadEvent = addonEvents.Startup.End
end

attach(savedVariableLoadEvent, AutoFishLive.OnSavedVariablesLoad, "AutoFish load saved variables")
attach(savedVariableSaveEvent, AutoFishLive.OnSavedVariablesSave, "AutoFish save saved variables")
attach(addonLoadEvent, AutoFishLive.OnStartup, "AutoFish addon load")

local systemEvents = Event and Event.System
local updateEvent = systemEvents and systemEvents.Update and systemEvents.Update.End
local secureEnterEvent = systemEvents and systemEvents.Secure and systemEvents.Secure.Enter
local secureLeaveEvent = systemEvents and systemEvents.Secure and systemEvents.Secure.Leave

local itemEvents = Event and Event.Item
local itemSlotEvent = itemEvents and itemEvents.Slot
local itemUpdateEvent = itemEvents and itemEvents.Update

attach(updateEvent, AutoFishLive.OnUpdateEnd, "AutoFish update")
attach(itemSlotEvent, function() queueRefresh("event.item_slot") end, "AutoFish item slot change")
attach(itemUpdateEvent, function() queueRefresh("event.item_update") end, "AutoFish item update")
attach(secureEnterEvent, function() queueRefresh("event.secure_enter") end, "AutoFish secure enter")
attach(secureLeaveEvent, function() queueRefresh("event.secure_leave") end, "AutoFish secure leave")
