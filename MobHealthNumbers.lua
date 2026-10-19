-- Copyright (c) 2026 Mario Debono. MIT license; see LICENSE.txt.
-- NPC-only presentation for our independent MobHealthLearning engine.
local settings={mode="target"}
local options={}
MobHealthNumbersOptions=options
local owned,restoring,elapsed=false,false,0
local function Number(value)
    local text=string.format("%.0f",value)
    local n
    repeat text,n=text:gsub("^(%-?%d+)(%d%d%d)","%1,%2") until n==0
    return text
end
local function IsMob(unit)
    local guid=UnitGUID(unit)
    return guid and guid:match("^Creature%-") and not UnitIsPlayer(unit)
end
local function Health(unit)
    if not IsMob(unit) then return end
    local hp,maximum=UnitHealth(unit),UnitHealthMax(unit)
    if not hp or not maximum or maximum<=0 then return end
    if maximum~=100 then return hp,maximum,false end
    if MobHealthLearning then
        local current,maxHP=MobHealthLearning.GetHealth(unit)
        if current and maxHP then return current,maxHP,true end
    end
    return nil,nil,true,hp
end
local function Bar() return TargetFrameHealthBar or (TargetFrame and TargetFrame.healthbar) end
local function Restore()
    if not owned then return end
    owned=false;restoring=true
    local bar=Bar()
    if bar and TextStatusBar_UpdateTextString then TextStatusBar_UpdateTextString(bar)
    elseif bar and bar.TextString then bar.TextString:SetText("") end
    restoring=false
end
local function Draw()
    if restoring then return end
    if settings.mode~="target" or not IsMob("target") then Restore();return end
    local bar=Bar()
    if not bar then return end
    if not bar.TextString then
        bar.TextString=(TargetFrameTextureFrame or bar):CreateFontString(nil,"OVERLAY","TextStatusBarText")
        bar.TextString:SetPoint("CENTER",bar,"CENTER",0,0)
    end
    local hp,maximum,estimated,percent=Health("target")
    local text=hp and Number(hp) or (percent and Number(percent).."%" or "")
    if bar.LeftText then bar.LeftText:SetText("") end
    if bar.RightText then bar.RightText:SetText("") end
    bar.TextString:SetText(text)
    if text~="" then bar.TextString:Show() end
    owned=true
end

-- One tooltip line, updated in place while hovering. The quiet secondary
-- surface labels estimates so the main target number needs no ~ prefix.
local function Tooltip(tooltip)
    if not tooltip:IsShown() then return end
    local _,unit=tooltip:GetUnit()
    if not unit or not IsMob(unit) then return end
    local hp,maximum,estimated,percent=Health(unit)
    local label=estimated and hp and "Estimated health" or "Health"
    local value=hp and (Number(hp).." / "..Number(maximum)) or (percent and Number(percent).."%" or nil)
    if not value then return end
    local row=tooltip.mobHPRow
    local name=tooltip:GetName()
    local left=row and name and _G[name.."TextLeft"..row]
    local right=row and name and _G[name.."TextRight"..row]
    if left and right then left:SetText(label);right:SetText(value)
    else
        tooltip:AddDoubleLine(label,value,1,.82,0,1,1,1)
        tooltip.mobHPRow=tooltip:NumLines()
    end
    tooltip:Show()
end
if GameTooltip then
    GameTooltip:HookScript("OnTooltipCleared",function(self) self.mobHPRow=nil end)
    GameTooltip:HookScript("OnTooltipSetUnit",Tooltip)
end
if TextStatusBar_UpdateTextStringWithValues then
    hooksecurefunc("TextStatusBar_UpdateTextStringWithValues",function(bar)
        if bar==Bar() then Draw() end
    end)
end
local frame=CreateFrame("Frame")
for _,event in ipairs({"ADDON_LOADED","PLAYER_ENTERING_WORLD","PLAYER_TARGET_CHANGED","UNIT_HEALTH","UNIT_HEALTH_FREQUENT","UNIT_MAXHEALTH"}) do frame:RegisterEvent(event) end
frame:SetScript("OnEvent",function(_,event,unit)
    if event=="ADDON_LOADED" then
        if unit~="MobHealthNumbers" then return end
        if type(MobHealthNumbersSettings)~="table" then MobHealthNumbersSettings={} end
        settings=MobHealthNumbersSettings
        if settings.mode~="target" and settings.mode~="hover" then settings.mode="target" end
    end
    if not event:find("^UNIT_") or unit=="target" then Draw() end
end)
frame:SetScript("OnUpdate",function(_,delta)
    elapsed=elapsed+delta
    if elapsed<.2 then return end
    elapsed=0;Draw()
    if GameTooltip then Tooltip(GameTooltip) end
end)
function options.GetSettings() return settings end
function options.SetMode(mode)
    if mode~="target" and mode~="hover" then return end
    settings.mode=mode
    Draw()
    if options.Refresh then options.Refresh() end
end
function options.SetPeers(enabled)
    MobHealthLearning.SetPeers(enabled==true)
    Draw()
    if options.Refresh then options.Refresh() end
end
SLASH_MOBHEALTHNUMBERS1="/mobhp"
SlashCmdList.MOBHEALTHNUMBERS=function(command)
    command=(command or ""):lower():match("^%s*(.-)%s*$"):gsub("%s+"," ")
    if command=="help" then
        print("Mob Health Numbers "..MobHealthLearning.Version.." - independent NPC learning and display by Mario Debono. MIT licensed.")
        print("/mobhp options - open display and peer-sharing settings")
        print("/mobhp mode target - current NPC HP on target bar and details on hover (default)")
        print("/mobhp mode hover - tooltip only; display choice is saved")
        print("/mobhp status - current mode, learned records and target information")
        print("/mobhp reset confirm - permanently clear learned and peer health records")
        print("Unknown health shows a percentage. Calculated health is labelled Estimated health in tooltips. Players are excluded.")
        print("/mobhp peers on | off - optional peer exchange (default on)")
        print("/mobhp commtest - one hidden self-whisper test; see README.md for limitations")
    elseif command=="options" or command=="settings" then
        options.Open()
    elseif command=="peers on" or command=="peers off" then
        options.SetPeers(command=="peers on")
    elseif command=="commtest" then
        MobHealthLearning.CommTest()
    elseif command=="mode hover" or command=="mode target" then
        options.SetMode(command=="mode hover" and "hover" or "target")
        print("Mob Health Numbers: "..(settings.mode=="hover" and "tooltip only." or "current HP on target bar; details on hover."))
    elseif command=="reset confirm" then
        MobHealthLearning.Reset();Draw()
        print("Mob Health Numbers: learned NPC health cleared.")
    elseif command=="reset" then
        print("Mob Health Numbers: this deletes all learned and peer health records. Type /mobhp reset confirm to continue.")
    elseif command=="" or command=="status" then
        MobHealthLearning.Status()
        print("Display mode: "..settings.mode..". /mobhp help - commands and credits")
    else
        print("Mob Health Numbers: unknown command. Use /mobhp help.")
    end
end
