-- Copyright (c) 2026 Mario Debono. MIT license; see LICENSE.txt.
-- Independent NPC health observations, encounter accounting and persistent cache.
local addonName = ...
local Engine = {}
Engine.Version=(GetAddOnMetadata and GetAddOnMetadata(addonName,"Version")) or "1.0.0"
MobHealthLearning = Engine
local encounters, peers, queue = {}, {}, {}
local database, settings, scope, peerScope, probe
local commState,commMessage="idle","Not tested."
local worldReady=false
local tick, sendAt, incomingAt, incomingCount = 0, 0, 0, 0
local PREFIX, MAX_HP, MAX_RECORDS = "MHN114v1", 1000000000, 4096
local function now() return GetTime() end
local function epoch() return time() end
local function integer(n, low, high)
    return type(n)=="number" and n==math.floor(n) and n>=low and n<=high
end
local function creature(guid)
    if type(guid)~="string" then return end
    local id = tonumber(guid:match("^Creature%-%d+%-%d+%-%d+%-%d+%-(%d+)%-"))
    if integer(id,1,10000000) then return id end
end
local ranks = {normal=true,elite=true,rare=true,rareelite=true,worldboss=true,trivial=true,minus=true}
local function identity(unit)
    local guid = UnitGUID(unit)
    local id = creature(guid)
    if not id or UnitIsPlayer(unit) then return end
    local level, rank = UnitLevel(unit), UnitClassification(unit) or "normal"
    if not integer(level,-1,255) or not ranks[rank] then return end
    return guid, id..":"..level..":"..rank
end
local function validKey(key)
    if type(key)~="string" or #key>48 then return false end
    local id,level,rank=key:match("^(%d+):(%-?%d+):(%a+)$")
    return integer(tonumber(id),1,10000000) and integer(tonumber(level),-1,255) and ranks[rank]
end
local function median(values)
    local sorted={}
    for i=1,#values do sorted[i]=values[i] end
    table.sort(sorted)
    local middle=math.floor(#sorted/2)+1
    if #sorted%2==1 then return sorted[middle] end
    return math.floor((sorted[middle-1]+sorted[middle])/2+.5)
end
local function prune(records)
    local count, oldest, oldestTime=0,nil,math.huge
    for key,r in pairs(records) do
        if type(r)~="table" or not validKey(key) or not integer(r.hp,1,MAX_HP) or
            not integer(r.seen,0,epoch()+86400) or epoch()-r.seen>180*86400 then
            records[key]=nil
        else
            count=count+1
            if r.seen<oldestTime then oldest,oldestTime=key,r.seen end
        end
    end
    if count>=MAX_RECORDS and oldest then records[oldest]=nil end
end
local function transmit(message,channel,target)
    if #queue<32 then queue[#queue+1]={message,channel,target} end
end
local function advertise(key,hp)
    if not settings.peers then return end
    local channel=IsInRaid() and "RAID" or (IsInGroup() and "PARTY" or nil)
    local message="H|"..peerScope.."|"..key.."|"..hp
    if channel then transmit(message,channel) end
    if IsInGuild() then transmit(message,"GUILD") end
end
local function fitsSamples(e,hp)
    for _,sample in ipairs(e.samples) do
        if math.abs(e.base-sample.net/hp-sample.pct)>.035 then return false end
    end
    return true
end
local function commit(e)
    if not database or e.invalid or not e.full or e.net<=0 then return end
    local hp
    if e.lastDamageKnown then
        hp=math.floor(e.net+.5)
    else
        -- Legacy servers do not supply overkill, even for the killing hit.
        -- Its raw damage is an upper bound, not the NPC's maximum health.
        -- Learn from multiple settled observations before death instead.
        local sample=e.samples[#e.samples]
        if #e.samples<2 or not sample or 1-sample.pct<.2 then return end
        hp=math.floor(sample.net/(1-sample.pct)+.5)
        if hp>e.net+math.max(1,hp*.015) then return end
    end
    if not integer(hp,1,MAX_HP) then return end
    -- Validate completed totals against settled interior observations. Missing
    -- log events or health resets must not silently poison a shared template.
    if not fitsSamples(e,hp) then return end
    local r=database.records[e.key]
    if not r then
        prune(database.records)
        r={history={},samples=0};database.records[e.key]=r
    end
    r.history=r.history or {}
    -- Do not average an old corrupted cache entry into a completed fight
    -- whose consistent observations have already disproved that maximum.
    if e.rejectedHP and e.rejectedHP==r.hp then r.history={} end
    if #r.history>=7 then table.remove(r.history,1) end
    r.history[#r.history+1]=hp
    r.hp=median(r.history)
    r.samples=math.min((r.samples or 0)+1,1000000)
    r.seen=epoch()
    advertise(e.key,r.hp)
end
local function count(records)
    local n=0;for _ in pairs(records) do n=n+1 end;return n
end
local function observe(unit)
    if not database then return end
    if UnitIsVisible and not UnitIsVisible(unit) then return end
    local guid,key=identity(unit)
    if not guid then return end
    local value,maximum=UnitHealth(unit),UnitHealthMax(unit)
    if type(value)~="number" or type(maximum)~="number" or maximum<=0 then return end
    -- Numeric API health takes priority and needs no estimator/cache entry.
    if maximum~=100 then return end
    local pct=math.max(0,math.min(1,value/maximum))
    local e=encounters[guid]
    if not e then
        if pct<=0 then return end
        if count(encounters)>=512 then
            local oldest,stamp=nil,math.huge
            for id,record in pairs(encounters) do
                if record.seen<stamp then oldest,stamp=id,record.seen end
            end
            encounters[oldest]=nil
        end
        local learned=database.records[key]
        local remote=settings.peers and peers[key]
        e={key=key,net=0,base= pct,full=pct==1,pct=pct,seen=now(),changed=now(),
            samples={},locked=learned and learned.hp or (remote and remote.hp),
            source=learned and "learned" or (remote and "peer" or nil)}
        encounters[guid]=e
    end
    if e.key~=key then e.invalid=true end
    if now()-e.seen>3 then e.invalid=true end
    e.seen=now()
    if pct~=e.pct then e.changed=now() end
    -- Out-of-combat refill/evade begins a new observation, discarding any tally.
    -- Never re-arm a dead GUID during the late-packet grace period.
    if not e.deadAt and pct==1 and e.pct<1 and UnitAffectingCombat and not UnitAffectingCombat(unit) then
        e.net=0;e.base=1;e.full=true;e.invalid=nil;e.samples={};e.estimate=nil;e.lastSample=nil
        e.lastDamageKnown=nil;e.logAt=nil
    end
    e.pct=pct
    if pct==0 and not e.deadAt and (not UnitIsDead or UnitIsDead(unit)) then e.deadAt=now() end
    return e
end
local function scan()
    observe("target");observe("mouseover")
    for unit in pairs(Engine.nameplates) do observe(unit) end
    -- Party/raid target tokens provide observations without requiring selection.
    local group=IsInRaid() and "raid" or "party"
    local size=GetNumGroupMembers and GetNumGroupMembers() or 0
    for i=1,math.min(size,40) do observe(group..i.."target") end
end
Engine.nameplates={}
local function combat()
    local event={CombatLogGetCurrentEventInfo()}
    local kind,dest=event[2],event[8]
    local e=encounters[dest]
    if not e then return end -- Never invent a full-health start from a log hit.
    if now()-e.seen>3 then e.invalid=true end
    local damage,overkill,healing,overheal
    if kind=="SWING_DAMAGE" then damage,overkill=event[12],event[13]
    elseif kind=="ENVIRONMENTAL_DAMAGE" then damage,overkill=event[13],event[14]
    elseif kind=="SPELL_DAMAGE" or kind=="SPELL_PERIODIC_DAMAGE" or kind=="RANGE_DAMAGE" or
        kind=="DAMAGE_SHIELD" or kind=="DAMAGE_SPLIT" or kind=="SPELL_BUILDING_DAMAGE" then
        damage,overkill=event[15],event[16]
    elseif kind=="SPELL_HEAL" or kind=="SPELL_PERIODIC_HEAL" then healing,overheal=event[15],event[16]
    elseif kind=="UNIT_DIED" or kind=="UNIT_DESTROYED" then e.deadAt=e.deadAt or now() end
    if damage then
        if not integer(damage,0,MAX_HP) then e.invalid=true;return end
        e.net=e.net+math.max(0,damage-math.max(0,tonumber(overkill) or 0))
        e.lastDamageKnown=integer(overkill,0,damage) and not (kind=="DAMAGE_SHIELD" and overkill==0)
        -- Some legacy packets use zero for an unavailable overkill field.
        -- Zero alone cannot prove death; wait for health/death events then.
        if e.lastDamageKnown and overkill>0 then e.deadAt=e.deadAt or now() end
        e.logAt=now()
    elseif healing then
        if not integer(healing,0,MAX_HP) then e.invalid=true;return end
        e.net=e.net-math.max(0,healing-math.max(0,tonumber(overheal) or 0))
        e.logAt=now()
    end
end
local function update(e)
    if e.invalid or e.deadAt or not e.logAt or now()-e.logAt<.2 or now()-e.changed<.2 then return end
    if e.full and e.pct==1 and e.net>0 and #e.samples>0 then e.invalid=true;return end
    if e.pct<=0 or e.pct>=e.base or e.net<=0 then return end
    -- Percentage quantization dominates tiny changes; wait for at least two
    -- points, then refine continuously. There is no arbitrary freeze threshold.
    local delta=e.base-e.pct
    if delta<.02 then return end
    local estimate=e.net/delta
    if estimate<1 or estimate>MAX_HP then return end
    if e.lastSample~=e.net then
        e.lastSample=e.net
        if #e.samples>=24 then table.remove(e.samples,1) end
        e.samples[#e.samples+1]={net=e.net,pct=e.pct}
        -- Later samples span more health and have less rounding error.
        e.estimate=math.floor(estimate+.5)
        if e.locked and #e.samples>=2 and delta>=.2 and
            math.abs(e.estimate-e.locked)/e.estimate>.15 and fitsSamples(e,e.estimate) then
            e.rejectedHP=e.locked;e.locked=nil;e.source=nil
        end
    end
end
function Engine.GetHealth(unit)
    local guid,key=identity(unit)
    if not guid then return end
    local hp,maxHP=UnitHealth(unit),UnitHealthMax(unit)
    if type(hp)~="number" or type(maxHP)~="number" or maxHP<=0 then return end
    if maxHP~=100 then return hp,maxHP,"direct" end
    local e=observe(unit)
    local learned=database and database.records[key]
    local remote=settings and settings.peers and peers[key]
    if e and e.rejectedHP then
        if learned and learned.hp==e.rejectedHP then learned=nil end
        if remote and remote.hp==e.rejectedHP then remote=nil end
    end
    if e and not e.locked and (learned or remote) then
        e.locked=learned and learned.hp or remote.hp
        e.source=learned and "learned" or "peer"
    end
    -- A visibility gap disqualifies learning from this fight, but does not
    -- erase an estimate already obtained for this GUID. Keep showing numeric
    -- HP from the current percentage without trusting the incomplete tally.
    local maximum=e and (e.locked or e.estimate) or
        (learned and learned.hp or (remote and remote.hp))
    if not maximum then return nil,nil,"unknown",hp end
    local current=math.floor(maximum*hp/100+.5)
    -- Use the net-damage count only when it agrees with the rounded API health.
    if e and e.full and not e.invalid then
        local counted=maximum-e.net
        if counted>=0 and math.abs(counted/maximum-hp/100)<=.015 then current=math.floor(counted+.5) end
    end
    current=math.max(0,math.min(maximum,current))
    return current,maximum,e and (e.source or "live") or "learned"
end
function Engine.GetStatus()
    local hp,maxHP,source,percent=Engine.GetHealth("target")
    return {localRecords=database and count(database.records) or 0,localLimit=MAX_RECORDS,
        peerRecords=count(peers),peerLimit=1024,scope=scope,peers=settings and settings.peers or false,
        targetCurrent=hp,targetMaximum=maxHP,targetSource=source,targetPercent=percent,
        commState=commState,commMessage=commMessage}
end
function Engine.Status()
    local status=Engine.GetStatus()
    print("Mob Health Numbers "..Engine.Version..": independent NPC learner. Local records "..
        status.localRecords..", peer records "..status.peerRecords..
        "; peers "..(status.peers and "on" or "off")..
        "; cache "..(status.scope or "waiting for realm")..".")
    local hp,maxHP,source=status.targetCurrent,status.targetMaximum,status.targetSource
    if source then print("Target: "..source..(hp and (" "..hp.." / "..maxHP) or " (percentage only)")) end
end
function Engine.Reset()
    if database then database.records={} end
    encounters={};peers={};queue={}
end
function Engine.SetPeers(enabled)
    settings.peers=enabled
    if not enabled then
        peers={};queue={}
        for _,e in pairs(encounters) do if e.source=="peer" then e.locked=nil;e.source=nil end end
    end
    print("Mob Health Numbers: peer exchange "..(enabled and "on." or "off."))
end
function Engine.CommTest()
    if probe then print("Mob Health Numbers: a self-whisper test is already pending.");return end
    if not C_ChatInfo or not C_ChatInfo.SendAddonMessage then
        commState,commMessage="unavailable","Addon messaging unavailable."
        print("Mob Health Numbers: addon messaging unavailable.");return
    end
    probe={token="P|"..tostring(now()),at=now()}
    commState,commMessage="pending","Waiting for a self-whisper reply..."
    local sent=pcall(C_ChatInfo.SendAddonMessage,PREFIX,probe.token,"WHISPER",UnitName("player"))
    if not sent then
        probe=nil;commState,commMessage="error","The test could not be sent."
        print("Mob Health Numbers: self-whisper test could not be sent.");return
    end
    print("Mob Health Numbers: sent one hidden self-whisper; no peer data sent.")
end
local function receive(prefix,message,channel,sender)
    if prefix~=PREFIX or type(message)~="string" or #message>160 then return end
    if probe and channel=="WHISPER" and type(sender)=="string" and
        sender:match("^[^-]+") == UnitName("player") and message==probe.token then
        commState,commMessage="success","Self-whisper received."
        print("Mob Health Numbers: self-whisper received; other channels remain unverified.");probe=nil;return
    end
    if not database or not settings.peers or (channel~="GUILD" and channel~="PARTY" and channel~="RAID") then return end
    if now()-incomingAt>=1 then incomingAt=now();incomingCount=0 end
    incomingCount=incomingCount+1
    if incomingCount>20 then return end
    local remoteScope,key,value=message:match("^H|([%w_%-]+)|([%w:%-]+)|(%d+)$")
    local hp=tonumber(value)
    if remoteScope~=peerScope or not validKey(key) or not integer(hp,1,MAX_HP) or database.records[key] then return end
    if count(peers)>=1024 and not peers[key] then return end
    peers[key]={hp=hp,seen=epoch()}
end
local function initialize()
    if type(MobHealthLearningDB)~="table" or (MobHealthLearningDB.version~=1 and MobHealthLearningDB.version~=2) then
        MobHealthLearningDB={version=2,realms={}}
    end
    if type(MobHealthLearningDB.realms)~="table" then MobHealthLearningDB.realms={} end
    if type(MobHealthNumbersSettings)~="table" then MobHealthNumbersSettings={} end
    settings=MobHealthNumbersSettings
    if type(settings.peers)~="boolean" then settings.peers=true end
    if C_ChatInfo and C_ChatInfo.RegisterAddonMessagePrefix then C_ChatInfo.RegisterAddonMessagePrefix(PREFIX) end
end
-- Compatibility lookup for old caches without keeping readable endpoints.
-- This is a lookup fingerprint, not encryption or an authentication mechanism.
local function legacyToken(value)
    local a,b=5381,52711
    for i=1,#value do
        local byte=value:byte(i)
        a=(a*33+byte)%4294967296;b=(b*65599+byte)%4294967296
    end
    return string.format("%08x%08x",a,b)
end
local function importRecords(saved, destination)
    if type(saved)~="table" or type(saved.records)~="table" then return end
    local n=count(destination.records)
    for key,r in pairs(saved.records) do
        if validKey(key) and type(r)=="table" and integer(r.hp,1,MAX_HP) and
            integer(r.seen,0,epoch()+86400) and epoch()-r.seen<=180*86400 then
            local previous=destination.records[key]
            if (previous or n<MAX_RECORDS) and (not previous or r.seen>previous.seen) then
                local history={}
                if type(r.history)=="table" then
                    for i=1,7 do if integer(r.history[i],1,MAX_HP) then history[#history+1]=r.history[i] end end
                end
                if #history==0 then history[1]=r.hp end
                destination.records[key]={hp=median(history),history=history,seen=r.seen,
                    samples=integer(r.samples,1,1000000) and r.samples or 1}
                if not previous then n=n+1 end
            end
        end
    end
end
local function bindRealm()
    -- Wait for the real realm instead of creating an unnamed loading cache.
    local realm=GetNormalizedRealmName and GetNormalizedRealmName()
    if type(realm)~="string" or realm=="" then realm=GetRealmName and GetRealmName() end
    if type(realm)~="string" or realm=="" then return end
    local resolved=realm:gsub("[^%w_%-]","_"):sub(1,64)
    if database and scope==resolved then return end
    local db=MobHealthLearningDB
    if db.version==1 then
        local migrated={version=2,realms={},legacy={}}
        local current={records={}}
        for oldScope,saved in pairs(db.realms) do
            if type(oldScope)=="string" then
                if oldScope==resolved or oldScope:sub(-#resolved-1)=="-"..resolved then
                    importRecords(saved,current)
                else
                    -- Keep other realms recoverable on their next visit without
                    -- saving their old portal/IP labels in the new database.
                    local preserved={records={}};importRecords(saved,preserved)
                    if next(preserved.records) then migrated.legacy[legacyToken(oldScope)]=preserved end
                end
            end
        end
        migrated.realms[resolved]=current
        MobHealthLearningDB=migrated;db=migrated
    end
    if type(db.legacy)~="table" then db.legacy={} end
    scope=resolved;peerScope=resolved;encounters={};peers={};queue={}
    database={records={}}
    importRecords(db.realms[scope],database)
    -- Read the old endpoint only when recovering a legacy bucket. Fresh
    -- databases, cache keys, UI and peer messages use the realm alone.
    if next(db.legacy) then
        local portal=GetCVar and GetCVar("portal")
        if type(portal)~="string" or portal=="" then portal="default" end
        local oldScope=(portal.."-"..realm):gsub("[^%w_%-]","_"):sub(1,64)
        local token=legacyToken(oldScope)
        importRecords(db.legacy[token],database);db.legacy[token]=nil
    end
    db.realms[scope]=database
end
local frame=CreateFrame("Frame")
for _,event in ipairs({"ADDON_LOADED","PLAYER_LOGIN","PLAYER_ENTERING_WORLD","PLAYER_TARGET_CHANGED","UPDATE_MOUSEOVER_UNIT",
    "UNIT_HEALTH","UNIT_HEALTH_FREQUENT","UNIT_MAXHEALTH","COMBAT_LOG_EVENT_UNFILTERED",
    "NAME_PLATE_UNIT_ADDED","NAME_PLATE_UNIT_REMOVED","CHAT_MSG_ADDON"}) do frame:RegisterEvent(event) end
frame:SetScript("OnEvent",function(_,event,...)
    local arg=...
    if event=="ADDON_LOADED" then if arg==addonName then initialize() end;return end
    if event=="PLAYER_LOGIN" or event=="PLAYER_ENTERING_WORLD" then
        if not settings then return end
        worldReady=true;bindRealm()
        if event=="PLAYER_ENTERING_WORLD" then encounters={};Engine.nameplates={} end
        scan();return
    end
    if event=="CHAT_MSG_ADDON" then receive(...);return end
    if not database then return end
    if event=="COMBAT_LOG_EVENT_UNFILTERED" then combat()
    elseif event=="NAME_PLATE_UNIT_ADDED" then Engine.nameplates[arg]=true;observe(arg)
    elseif event=="NAME_PLATE_UNIT_REMOVED" then Engine.nameplates[arg]=nil
    elseif event:find("^UNIT_") then observe(arg)
    else scan() end
end)
frame:SetScript("OnUpdate",function(_,elapsed)
    tick=tick+elapsed;if tick<.1 then return end;tick=0
    if probe and now()-probe.at>5 then
        commState,commMessage="timeout","No reply received."
        print("Mob Health Numbers: self-whisper timed out; routing remains unconfirmed.");probe=nil
    end
    if worldReady and not database then bindRealm() end
    if not database then return end
    scan()
    for guid,e in pairs(encounters) do
        if e.deadAt and now()-math.max(e.deadAt,e.logAt or 0)>.65 then commit(e);encounters[guid]=nil
        elseif now()-e.seen>60 then encounters[guid]=nil
        else update(e) end
    end
    for key,r in pairs(peers) do if epoch()-r.seen>900 then peers[key]=nil end end
    if #queue>0 and settings.peers and now()>=sendAt then
        local item=table.remove(queue,1);sendAt=now()+1
        if C_ChatInfo and C_ChatInfo.SendAddonMessage then C_ChatInfo.SendAddonMessage(PREFIX,unpack(item)) end
    end
end)
