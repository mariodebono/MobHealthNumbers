-- Copyright (c) 2026 Mario Debono. MIT license; see LICENSE.txt.
local addonName=...
local options=MobHealthNumbersOptions
local panel,content,target,sharing,localCount,peerCount,realmText,targetText,testButton,testResult
local elapsed=0

local function label(parent,text,x,y,font,width)
    local region=parent:CreateFontString(nil,"ARTWORK",font or "GameFontHighlightSmall")
    region:SetPoint("TOPLEFT",parent,"TOPLEFT",x,y)
    region:SetWidth(width or 480)
    region:SetJustifyH("LEFT")
    region:SetText(text)
    return region
end
local function number(value)
    local text=string.format("%.0f",value)
    local changed
    repeat text,changed=text:gsub("^(%d+)(%d%d%d)","%1,%2") until changed==0
    return text
end
local function divider(y)
    local line=content:CreateTexture(nil,"ARTWORK")
    line:SetPoint("TOPLEFT",content,"TOPLEFT",0,y)
    line:SetSize(480,1)
    line:SetColorTexture(1,.82,0,.2)
end
local function checkbox(name,text,y,callback)
    local button=CreateFrame("CheckButton",name,content,"UICheckButtonTemplate")
    button:SetPoint("TOPLEFT",content,"TOPLEFT",8,y)
    button:SetSize(26,26)
    local caption=button:CreateFontString(nil,"ARTWORK","GameFontHighlight")
    caption:SetPoint("LEFT",button,"RIGHT",4,0)
    caption:SetText(text)
    button:SetScript("OnClick",function(self) callback(not not self:GetChecked()) end)
    return button
end
local sourceNames={direct="reported",learned="learned",peer="received",live="estimated"}
local colors={idle="|cffaaaaaa",pending="|cffffd166",success="|cff80d69c",
    timeout="|cffff9c85",unavailable="|cffff9c85",error="|cffff9c85"}
function options.RefreshStats()
    if not panel then return end
    local status=MobHealthLearning.GetStatus()
    localCount:SetText(number(status.localRecords).." / "..number(status.localLimit))
    peerCount:SetText(number(status.peerRecords).." / "..number(status.peerLimit))
    realmText:SetText(status.scope or "Waiting for realm information...")
    if status.targetCurrent then
        targetText:SetText(number(status.targetCurrent).." / "..number(status.targetMaximum)..
            " HP ("..(sourceNames[status.targetSource] or status.targetSource)..")")
    elseif status.targetSource then
        targetText:SetText(number(status.targetPercent or 0).."% (not yet learned)")
    else targetText:SetText("Select an NPC to see its health source.") end
    testResult:SetText((colors[status.commState] or colors.idle)..status.commMessage.."|r")
    testButton:SetEnabled(status.commState~="pending")
end
function options.Refresh()
    if not panel then return end
    local saved=options.GetSettings()
    target:SetChecked(saved.mode=="target")
    sharing:SetChecked(saved.peers==true)
    options.RefreshStats()
end
local function create()
    if panel then return true end
    if not InterfaceOptions_AddCategory then return false end
    panel=CreateFrame("Frame","MobHealthNumbersOptionsPanel",InterfaceOptionsFramePanelContainer)
    panel.name="Mob Health Numbers"
    label(panel,"Mob Health Numbers",16,-16,"GameFontNormalLarge")
    label(panel,"NPC health learning and display | "..MobHealthLearning.Version,16,-42)

    local scroll=CreateFrame("ScrollFrame","MobHealthNumbersOptionsScroll",panel,"UIPanelScrollFrameTemplate")
    scroll:SetPoint("TOPLEFT",panel,"TOPLEFT",16,-68)
    scroll:SetPoint("BOTTOMRIGHT",panel,"BOTTOMRIGHT",-32,56)
    content=CreateFrame("Frame",nil,scroll)
    content:SetSize(500,564)
    scroll:SetScrollChild(content)

    label(content,"Display",0,0,"GameFontNormal")
    target=checkbox("MobHealthNumbersTargetOption","Show current HP on the target frame",-24,function(checked)
        options.SetMode(checked and "target" or "hover")
    end)
    label(content,"Turn off for tooltip-only mode. Mouseover details remain available,\nwith calculated health labelled as estimated.",38,-56,nil,442)
    divider(-100)

    label(content,"Peer sharing",0,-116,"GameFontNormal")
    sharing=checkbox("MobHealthNumbersSharingOption","Share learned health with other addon users",-140,options.SetPeers)
    label(content,"On by default. Shares with compatible guild and party/raid members.\nLocal observations take priority; WoW identifies the sender.",38,-172,nil,442)
    divider(-216)

    label(content,"Cache and current target",0,-232,"GameFontNormal")
    label(content,"LEARNED LOCALLY",8,-260,"GameFontHighlightSmall",220)
    label(content,"RECEIVED FROM PEERS",260,-260,"GameFontHighlightSmall",220)
    localCount=label(content,"",8,-280,"GameFontNormalLarge",220)
    peerCount=label(content,"",260,-280,"GameFontNormalLarge",220)
    label(content,"Counts creature types and levels, not individual kills. Peer records expire.",8,-310,nil,472)
    label(content,"Realm cache",8,-338,"GameFontNormal",472)
    realmText=label(content,"",8,-356,nil,472)
    label(content,"Current target",8,-382,"GameFontNormal",472)
    targetText=label(content,"",8,-400,nil,472)
    divider(-432)

    label(content,"Communications check",0,-448,"GameFontNormal")
    testButton=CreateFrame("Button","MobHealthNumbersCommTestOption",content,"UIPanelButtonTemplate")
    testButton:SetSize(176,24)
    testButton:SetPoint("TOPLEFT",content,"TOPLEFT",8,-474)
    testButton:SetText("Test communications")
    testButton:SetScript("OnClick",function() MobHealthLearning.CommTest();options.RefreshStats() end)
    testResult=label(content,"",200,-479,"GameFontHighlightSmall",280)
    label(content,"Sends one hidden whisper to yourself. Guild and party/raid routes\nneed another addon user to verify. Sharing can stay off for this test.",8,-514,nil,472)

    local defaults=CreateFrame("Button","MobHealthNumbersDefaultsOption",panel,"UIPanelButtonTemplate")
    defaults:SetSize(140,24)
    defaults:SetPoint("BOTTOMLEFT",panel,"BOTTOMLEFT",16,16)
    defaults:SetText("Restore defaults")
    defaults:SetScript("OnClick",function() options.SetMode("target");options.SetPeers(true) end)
    local footer=panel:CreateFontString(nil,"ARTWORK","GameFontHighlightSmall")
    footer:SetPoint("LEFT",defaults,"RIGHT",12,0)
    footer:SetText("Your learned health records are kept.")

    panel.localCount=localCount;panel.peerCount=peerCount;panel.realmText=realmText
    panel.targetText=targetText;panel.testResult=testResult
    panel:SetScript("OnShow",function() elapsed=0;options.Refresh() end)
    panel:SetScript("OnUpdate",function(self,delta)
        if not self:IsShown() then return end
        elapsed=elapsed+delta
        if elapsed>=.5 then elapsed=0;options.RefreshStats() end
    end)
    panel.refresh=options.Refresh
    InterfaceOptions_AddCategory(panel)
    options.Refresh()
    return true
end
function options.Open()
    if create() and InterfaceOptionsFrame_OpenToCategory then
        InterfaceOptionsFrame_OpenToCategory(panel)
        InterfaceOptionsFrame_OpenToCategory(panel)
    else print("Mob Health Numbers: settings panel unavailable. Use /mobhp help for chat controls.") end
end
local events=CreateFrame("Frame")
events:RegisterEvent("ADDON_LOADED")
events:SetScript("OnEvent",function(_,_,name) if name==addonName then create() end end)
