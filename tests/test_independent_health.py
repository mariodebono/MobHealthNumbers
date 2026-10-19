"""Lua 5.1 health learning, display and command contract tests."""
from pathlib import Path
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
FIXTURE=(ROOT/'tests/mob_health_fixture.lua').read_text()
WORLD=r'''
frames={};outgoing={};isGuild=false;isGroup=false;realm="TestRealm";portal="test";inCombat=true
function GetNormalizedRealmName() return realm end
function GetCVar() return portal end
function UnitName() return "Tester" end
function UnitAffectingCombat() return inCombat end
function UnitGUID(unit) if unit=="target" and target then return guid end end
function IsInGuild() return isGuild end
function IsInGroup() return isGroup end
function IsInRaid() return false end
function GetNumGroupMembers() return 0 end
function CreateFrame()
 local f={events={}}
 function f:RegisterEvent(e) self.events[e]=true end
 function f:SetScript(e,fn) self[e]=fn end
 frames[#frames+1]=f;return f
end
function fire(e,...)
 for _,f in ipairs(frames) do if f.events[e] and f.OnEvent then f.OnEvent(f,e,...) end end
end
function advance(seconds)
 local n=math.ceil(seconds/.05)
 for i=1,n do
  clock=clock+seconds/n
  for _,f in ipairs(frames) do if f.OnUpdate then f.OnUpdate(f,seconds/n) end end
 end
end
function TextStatusBar_UpdateTextString(bar) bar.TextString:SetText("native") end
C_ChatInfo={RegisterAddonMessagePrefix=function(p) registered=p end,
 SendAddonMessage=function(...) outgoing[#outgoing+1]={...} end}
function records() return MobHealthLearningDB.realms[realm].records end
function dead(amount,over)
 combat("SWING_DAMAGE",amount,over or 0);hp=0;fire("UNIT_HEALTH","target")
 combat("UNIT_DIED");advance(1)
end
function selectMob(id,percent)
 guid="Creature-0-1-2-3-"..id.."-00000002";hp=percent or 100
 fire("PLAYER_TARGET_CHANGED");advance(.1)
end
'''
checks=0
def new(pre='',saved='',enter_world=True):
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute(FIXTURE);lua.execute(WORLD)
    lua.execute(pre);lua.execute(saved)
    loader=lua.eval('function(s,n) return assert(loadstring(s,n)) end')
    folder=ROOT
    for line in (folder/'MobHealthNumbers.toc').read_text().splitlines():
        if line.endswith('.lua'): loader((folder/line).read_text(),line)('MobHealthNumbers')
    lua.globals().fire('ADDON_LOADED','MobHealthNumbers')
    if enter_world:
        lua.globals().fire('PLAYER_ENTERING_WORLD')
        lua.globals().fire('PLAYER_TARGET_CHANGED')
        lua.globals().advance(.1)
    return lua
def check(lua,code):
    global checks
    lua.execute(code);checks+=1

lua=new()
check(lua,'assert(shown()=="100%" and #outgoing==0 and RealMobHealth114==nil)')
check(lua,'hit(100,90);local h,m,s=MobHealthLearning.GetHealth("target");assert(h==900 and m==1000 and s=="live")')
check(lua,'hit(100,80,false,"Player-0-OTHER");assert(shown()=="800")')
check(lua,'dead(900,100);assert(records()["1234:10:normal"].hp==1000 and records()["1234:10:normal"].samples==1)')
check(lua,'selectMob(1234);assert(shown()=="1,000")')
check(lua,'hit(200,80);assert(shown()=="800");local _,m=MobHealthLearning.GetHealth("target");assert(m==1000)')
check(lua,'hit(80,70);local _,m=MobHealthLearning.GetHealth("target");assert(m==1000)')

for health_first in ('true','false'):
    lua=new()
    check(lua,f'hit(100,90,{health_first});hit(900,0,{health_first},nil,nil,0);combat("UNIT_DIED");advance(1);assert(records()["1234:10:normal"].hp==1000)')
lua=new()
check(lua,'hp=0;fire("UNIT_HEALTH","target");advance(.3);combat("SWING_DAMAGE",1000,0);advance(1);assert(records()["1234:10:normal"].hp==1000)')
lua=new('hp=60')
check(lua,'hit(100,50);local _,m=MobHealthLearning.GetHealth("target");assert(m==1000);dead(500);assert(next(records())==nil)')
# The fixture emits heal immediately, so use an explicit event for overheal.
lua=new()
check(lua,'hit(200,80);log={clock,"SPELL_HEAL",false,"Player-0-HEAL","healer",0,0,guid,"mob",0,0,1,"heal",1,100,50};fire("COMBAT_LOG_EVENT_UNFILTERED");hp=85;fire("UNIT_HEALTH","target");advance(.5);dead(850);assert(records()["1234:10:normal"].hp==1000)')
lua=new()
check(lua,'hit(100,90);combat("SWING_MISSED",0);dead(900);assert(records()["1234:10:normal"].hp==1000)')
for event in ('SPELL_DAMAGE','SPELL_PERIODIC_DAMAGE','RANGE_DAMAGE','DAMAGE_SHIELD','DAMAGE_SPLIT','ENVIRONMENTAL_DAMAGE','SPELL_BUILDING_DAMAGE'):
    lua=new()
    check(lua,f'hit(200,80,false,nil,"{event}");hit(300,50,false,nil,"{event}");hit(500,0,false,nil,"{event}",0);combat("UNIT_DIED");advance(1);assert(records()["1234:10:normal"].hp==1000)')
lua=new()
check(lua,'hit(100,50);dead(500);assert(next(records())==nil)') # missed damage fails settled percentage validation
lua=new()
check(lua,'target=false;advance(4);combat("SWING_DAMAGE",1000,0);advance(1);assert(next(records())==nil)')
lua=new()
check(lua,'hit(100,90);hp=100;inCombat=false;fire("UNIT_HEALTH","target");inCombat=true;hit(100,90);dead(900);assert(records()["1234:10:normal"].hp==1000)')
lua=new()
check(lua,'hit(100,90);hp=100;fire("UNIT_HEALTH","target");advance(.4);dead(1000);assert(next(records())==nil)') # unlogged combat refill
lua=new('player=true;guid="Player-0-OTHER"')
check(lua,'assert(MobHealthLearning.GetHealth("target")==nil);hit(100,90);dead(900);assert(next(records())==nil)')
lua=new('guid="Pet-0-1-2-3-1234-00000001"')
check(lua,'assert(MobHealthLearning.GetHealth("target")==nil)')
lua=new('hp=347;maximum=520')
check(lua,'local h,m,s=MobHealthLearning.GetHealth("target");assert(h==347 and m==520 and s=="direct" and shown()=="347")')
saved='MobHealthLearningDB={version=1,realms={["test-TestRealm"]={records={["1234:10:normal"]={hp=1000,seen=1700000000,samples=2,history={1000,1000}}}}}}'
lua=new(saved=saved)
check(lua,'assert(shown()=="1,000");assert(records()["1234:10:normal"].samples==2)')
lua=new('realm="OtherRealm"',saved)
check(lua,'assert(shown()=="100%" and next(records())==nil)')
lua=new(saved=saved)
check(lua,'dead(100000);selectMob(1234);assert(shown()=="1,000")') # median protects single outlier
lua=new(saved=saved)
check(lua,'SlashCmdList.MOBHEALTHNUMBERS("reset");assert(records()["1234:10:normal"].hp==1000)')
check(lua,'SlashCmdList.MOBHEALTHNUMBERS(" RESET  CONFIRM ");assert(next(records())==nil)')
check(lua,'SlashCmdList.MOBHEALTHNUMBERS("HELP");assert(messages[#messages]:find("commtest",1,true))')
check(lua,'SlashCmdList.MOBHEALTHNUMBERS(" MODE  HOVER ");assert(shown()=="native" and MobHealthNumbersSettings.mode=="hover")')
check(lua,'SlashCmdList.MOBHEALTHNUMBERS("MODE TARGET");assert(shown()=="100%")')
check(lua,'SlashCmdList.MOBHEALTHNUMBERS("nonsense");assert(messages[#messages]:find("unknown command",1,true))')
lua=new('isGuild=true;MobHealthNumbersSettings={peers=false}')
check(lua,'dead(1000);assert(#outgoing==0)')
check(lua,'SlashCmdList.MOBHEALTHNUMBERS("peers on");selectMob(5678);dead(2000);advance(2);assert(#outgoing==1 and outgoing[1][1]=="MHN114v1" and outgoing[1][3]=="GUILD")')
check(lua,'fire("CHAT_MSG_ADDON","MHN114v1","H|TestRealm|9999:10:normal|2500","GUILD","Friend");selectMob(9999);assert(shown()=="2,500")')
check(lua,'fire("CHAT_MSG_ADDON","MHN114v1","H|TestRealm|9999:10:normal|9000","GUILD","Friend");local _,m=MobHealthLearning.GetHealth("target");assert(m==2500)')
check(lua,'SlashCmdList.MOBHEALTHNUMBERS("peers off");assert(shown()~="2,500");local h=MobHealthLearning.GetHealth("target");assert(h==nil)')
lua=new('MobHealthNumbersSettings={peers=true}')
check(lua,'fire("CHAT_MSG_ADDON","MHN114v1","H|wrongrealm|1234:10:normal|9000","GUILD","Friend");assert(shown()=="100%")')
check(lua,'fire("CHAT_MSG_ADDON","MHN114v1","H|TestRealm|1234:10:normal|999999999999","GUILD","Friend");assert(shown()=="100%")')
check(lua,'fire("CHAT_MSG_ADDON","MHN114v1","H|TestRealm|1234:10:normal|9000","YELL","Friend");assert(shown()=="100%")')
check(lua,'fire("CHAT_MSG_ADDON","RMH","1234-10:9000","GUILD","Friend");assert(shown()=="100%")')
lua=new()
check(lua,'SlashCmdList.MOBHEALTHNUMBERS("commtest");SlashCmdList.MOBHEALTHNUMBERS("commtest");assert(#outgoing==1 and outgoing[1][3]=="WHISPER")')
check(lua,'fire("CHAT_MSG_ADDON","MHN114v1",outgoing[1][2],"WHISPER","Tester-TestRealm");assert(messages[#messages]:find("received",1,true))')
check(lua,'SlashCmdList.MOBHEALTHNUMBERS("commtest");advance(6);assert(messages[#messages]:find("unconfirmed",1,true))')
lua=new(saved='MobHealthLearningDB={version=1,realms={["test-TestRealm"]={records={bad=true,["1234:10:normal"]={hp=-1,seen=1700000000}}}}}')
check(lua,'assert(next(records())==nil)')
lua=new()
check(lua,'hit(1,100);hit(99,90);dead(900);assert(records()["1234:10:normal"].hp==1000)') # integer percentage rounding at first hit
lua=new()
check(lua,'hit(200,80);combat("SPELL_PERIODIC_HEAL",100);hp=90;fire("UNIT_HEALTH","target");advance(.5);dead(900);assert(records()["1234:10:normal"].hp==1000)')
lua=new()
check(lua,'hit(100,90);UnitIsVisible=function() return false end;advance(4);dead(900);assert(next(records())==nil)')
lua=new()
check(lua,'hit(100,90);target=false;advance(61);target=true;dead(900);assert(next(records())==nil)')
lua=new()
check(lua,'for i=1,30 do hit(10,100-i) end;dead(700);assert(records()["1234:10:normal"].hp==1000)')
lua=new()
check(lua,'hit(100,90);fire("PLAYER_ENTERING_WORLD");dead(900);assert(next(records())==nil)')
lua=new('MobHealthNumbersSettings={mode="hover"}')
check(lua,'assert(MobHealthNumbersSettings.mode=="hover")')
lua=new(saved='MobHealthLearningDB={version=999,realms={}}')
check(lua,'assert(MobHealthLearningDB.version==2 and next(records())==nil)')
lua=new(saved='MobHealthLearningDB={version=1,realms={["test-TestRealm"]={records={["1234:10:normal"]={hp=1000,seen=1}}}}}')
check(lua,'assert(next(records())==nil)')
TOOLTIP=r'''
hoverGUID="Creature-0-1-2-3-1234-00000003";hoverHP=100;hoverMax=100;hoverPlayer=false
local oldGUID,oldHP,oldMax,oldPlayer=UnitGUID,UnitHealth,UnitHealthMax,UnitIsPlayer
function UnitGUID(unit) if unit=="mouseover" then return hoverGUID end return oldGUID(unit) end
function UnitHealth(unit) if unit=="mouseover" then return hoverHP end return oldHP(unit) end
function UnitHealthMax(unit) if unit=="mouseover" then return hoverMax end return oldMax(unit) end
function UnitIsPlayer(unit) if unit=="mouseover" then return hoverPlayer end return oldPlayer(unit) end
GameTooltip={scripts={},lines=0}
function GameTooltip:HookScript(e,fn) self.scripts[e]=fn end
function GameTooltip:GetUnit() return "Mob","mouseover" end
function GameTooltip:IsShown() return true end
function GameTooltip:GetName() return "GameTooltip" end
function GameTooltip:NumLines() return self.lines end
function GameTooltip:Show() end
function GameTooltip:AddDoubleLine(left,right)
 self.lines=self.lines+1
 _G["GameTooltipTextLeft"..self.lines]=text();_G["GameTooltipTextRight"..self.lines]=text()
 _G["GameTooltipTextLeft"..self.lines]:SetText(left);_G["GameTooltipTextRight"..self.lines]:SetText(right)
end
function hover() GameTooltip.scripts.OnTooltipSetUnit(GameTooltip) end
function clearTooltip() GameTooltip.lines=0;GameTooltip.scripts.OnTooltipCleared(GameTooltip) end
'''
lua=new(TOOLTIP,saved)
check(lua,'hover();assert(GameTooltip.lines==1 and GameTooltipTextRight1.text=="1,000 / 1,000" and GameTooltipTextLeft1.text=="Estimated health")')
check(lua,'hoverHP=75;advance(.5);assert(GameTooltip.lines==1 and GameTooltipTextRight1.text=="750 / 1,000")')
check(lua,'clearTooltip();hoverGUID="Player-0-OTHER";hoverPlayer=true;hover();advance(.5);assert(GameTooltip.lines==0)')
check(lua,'hoverPlayer=false;hoverGUID="Creature-0-1-2-3-5678-00000003";hoverHP=80;hover();assert(GameTooltipTextRight1.text=="80%")')
check(lua,'hoverMax=520;hoverHP=347;advance(.5);assert(GameTooltipTextLeft1.text=="Health" and GameTooltipTextRight1.text=="347 / 520" and GameTooltip.lines==1)')
check(lua,'SlashCmdList.MOBHEALTHNUMBERS("mode hover");assert(shown()=="native");advance(1);assert(shown()=="native")')
lua=new('local oldGUID=UnitGUID;function UnitGUID(u) if u=="nameplate1" then return "Creature-0-1-2-3-5678-00000001" end return oldGUID(u) end')
check(lua,'fire("NAME_PLATE_UNIT_ADDED","nameplate1");combat("SWING_DAMAGE",1000,0,"Creature-0-1-2-3-5678-00000001");combat("UNIT_DIED",nil,nil,"Creature-0-1-2-3-5678-00000001");advance(1);assert(records()["5678:10:normal"].hp==1000)')
lua=new('MobHealthNumbersSettings={peers=true}')
check(lua,'for i=1,100 do fire("CHAT_MSG_ADDON","MHN114v1","H|TestRealm|"..(10000+i)..":10:normal|1000","GUILD","Flood") end;local _,n=0,0;selectMob(10100);local hp=MobHealthLearning.GetHealth("target");assert(hp==nil)')
lua=new('MobHealthNumbersSettings={peers=true}',saved)
check(lua,'fire("CHAT_MSG_ADDON","MHN114v1","H|TestRealm|1234:10:normal|9999","GUILD","Other");assert(shown()=="1,000")')
# Realm sharing works across different login proxies without sharing endpoints.
sender=new('portal="proxy-a";isGuild=true')
check(sender,'dead(1000);advance(2);assert(#outgoing==1 and outgoing[1][2]=="H|TestRealm|1234:10:normal|1000");'
      'assert(MobHealthLearningDB.realms["TestRealm"].records["1234:10:normal"].hp==1000)')
recipient=new('portal="proxy-b"')
recipient.globals().shared_message=sender.globals().outgoing[1][2]
check(recipient,'fire("CHAT_MSG_ADDON","MHN114v1",shared_message,"GUILD","Friend");advance(.3);'
      'assert(shown()=="1,000" and MobHealthLearning.GetStatus().peerRecords==1);'
      'assert(next(MobHealthLearningDB.realms["TestRealm"].records)==nil)')
lua=new('portal="proxy-b"',saved)
check(lua,'assert(shown()=="1,000" and records()["1234:10:normal"].hp==1000);'
      'assert(MobHealthLearningDB.realms["test-TestRealm"]==nil and MobHealthLearning.GetStatus().scope=="TestRealm")')
lua=new()
check(lua,'SlashCmdList.MOBHEALTHNUMBERS("help");local found=false;for _,message in ipairs(messages) do '
      'if message:find("optional peer exchange (default on)",1,true) then found=true end end;assert(found)')
# Model-based fights: independently compute real remaining health, quantize the
# exposed percentage, then ensure the learner reconstructs the completed total.
import random
randomizer=random.Random(11402)
for case in range(40):
    lua=new()
    maximum=randomizer.randint(150,1000000)
    remaining=maximum
    for step in range(8):
        amount=min(remaining-1,max(1,int(maximum*randomizer.uniform(.025,.09))))
        if amount<=0: break
        remaining-=amount
        percent=int(100*remaining/maximum+.5)
        lua.execute(f'hit({amount},{percent},{"true" if step%2 else "false"},"Player-0-{step%3}")')
        if step in (3,5):
            effective=max(1,int((maximum-remaining)*.13));remaining+=effective
            percent=int(100*remaining/maximum+.5)
            lua.execute(f'log={{clock,"SPELL_HEAL",false,"Player-0-HEAL","healer",0,0,guid,"mob",0,0,1,"heal",1,{effective+20},20}};fire("COMBAT_LOG_EVENT_UNFILTERED");hp={percent};fire("UNIT_HEALTH","target");advance(.4)')
    overkill=randomizer.randint(0,maximum)
    check(lua,f'dead({remaining+overkill},{overkill});assert(records()["1234:10:normal"].hp=={maximum})')
print(f'PASS: {checks} independent engine, display and command checks (Lua 5.1), including 40 model-based multi-attacker/healing fights')
