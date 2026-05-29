-- Lightweight JSON-to-table parser for inbound bridge commands.
-- Supports objects, arrays, strings (with escape sequences), numbers, booleans, and null.
-- Returns (table, nil) on success, or (nil, errorMessage) on parse failure.

local JsonParser = {}

function JsonParser.parse(json)
  if type(json) ~= "string" then
    return nil, "input must be a string"
  end

  local text = string.match(json, "^%s*(.-)%s*$")
  if text == nil or text == "" then
    return nil, "empty input"
  end

  local pos = 1

  -- Forward declarations for mutually-recursive functions
  local skipSpace, parseString, parseObject, parseArray, parseValue

  skipSpace = function()
    while pos <= #text do
      local c = string.sub(text, pos, pos)
      if c == " " or c == "\t" or c == "\n" or c == "\r" then
        pos = pos + 1
      else
        break
      end
    end
  end

  parseString = function()
    skipSpace()
    if string.sub(text, pos, pos) ~= '"' then
      return nil, "expected string"
    end
    pos = pos + 1
    local parts = {}
    while pos <= #text do
      local c = string.sub(text, pos, pos)
      if c == '"' then
        pos = pos + 1
        return table.concat(parts)
      elseif c == "\\" then
        local nxt = string.sub(text, pos + 1, pos + 1)
        local escTable = { ['"'] = '"', ['\\'] = '\\', ['/'] = '/', ['b'] = '\b', ['f'] = '\f', ['n'] = '\n', ['r'] = '\r', ['t'] = '\t' }
        if escTable[nxt] then
          parts[#parts + 1] = escTable[nxt]
          pos = pos + 2
        elseif nxt == 'u' then
          parts[#parts + 1] = string.sub(text, pos, pos + 5)
          pos = pos + 6
        else
          parts[#parts + 1] = nxt
          pos = pos + 2
        end
      else
        parts[#parts + 1] = c
        pos = pos + 1
      end
    end
    return nil, "unterminated string"
  end

  parseObject = function()
    skipSpace()
    pos = pos + 1  -- consume '{'
    skipSpace()
    if pos <= #text and string.sub(text, pos, pos) == '}' then
      pos = pos + 1
      return {}
    end
    local obj = {}
    while pos <= #text do
      skipSpace()
      local key, err = parseString()
      if key == nil then
        return nil, "object key: " .. tostring(err)
      end
      skipSpace()
      if string.sub(text, pos, pos) ~= ':' then
        return nil, "expected ':' in object"
      end
      pos = pos + 1
      local val, valErr = parseValue()
      if valErr then
        return nil, "object value for key " .. tostring(key) .. ": " .. valErr
      end
      obj[key] = val
      skipSpace()
      local c = string.sub(text, pos, pos)
      if c == '}' then
        pos = pos + 1
        return obj
      elseif c == ',' then
        pos = pos + 1
      else
        return nil, "expected ',' or '}' in object"
      end
    end
    return nil, "unterminated object"
  end

  parseArray = function()
    skipSpace()
    pos = pos + 1  -- consume '['
    skipSpace()
    if pos <= #text and string.sub(text, pos, pos) == ']' then
      pos = pos + 1
      return {}
    end
    local arr = {}
    while pos <= #text do
      skipSpace()
      local val, valErr = parseValue()
      if valErr then
        return nil, "array element: " .. valErr
      end
      arr[#arr + 1] = val
      skipSpace()
      local c = string.sub(text, pos, pos)
      if c == ']' then
        pos = pos + 1
        return arr
      elseif c == ',' then
        pos = pos + 1
      else
        return nil, "expected ',' or ']' in array"
      end
    end
    return nil, "unterminated array"
  end

  parseValue = function()
    skipSpace()
    if pos > #text then
      return nil, "unexpected end"
    end
    local c = string.sub(text, pos, pos)
    if c == '{' then
      return parseObject()
    elseif c == '[' then
      return parseArray()
    elseif c == '"' then
      return parseString()
    elseif c == 't' then
      if string.sub(text, pos, pos + 3) == "true" then
        pos = pos + 4
        return true
      end
      return nil, "expected true"
    elseif c == 'f' then
      if string.sub(text, pos, pos + 4) == "false" then
        pos = pos + 5
        return false
      end
      return nil, "expected false"
    elseif c == 'n' then
      if string.sub(text, pos, pos + 3) == "null" then
        pos = pos + 4
        return nil
      end
      return nil, "expected null"
    else
      -- Number: try patterns in order of specificity
      local numStr = string.match(text, "^-?[0-9]+%.[0-9]+[eE][+-]?[0-9]+", pos)  -- float with exponent
        or string.match(text, "^-?[0-9]+[eE][+-]?[0-9]+", pos)  -- integer with exponent
        or string.match(text, "^-?[0-9]+%.[0-9]+", pos)  -- decimal number
        or string.match(text, "^-?[0-9]+", pos)  -- plain integer
      if numStr then
        pos = pos + #numStr
        local num = tonumber(numStr)
        if num ~= nil then
          return num
        end
        return nil, "invalid number"
      end
      return nil, "unexpected character"
    end
  end

  skipSpace()
  local result, err = parseValue()
  if err then
    return nil, err
  end
  skipSpace()
  if pos <= #text then
    return nil, "trailing characters after value"
  end
  return result
end

AutoFish = AutoFish or {}
AutoFish.Bridge = AutoFish.Bridge or {}
AutoFish.Bridge.JsonParser = JsonParser
if require ~= nil then return JsonParser end
