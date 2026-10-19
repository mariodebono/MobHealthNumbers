
clock=0; hp=100; maximum=100; target=true; player=false; party=false
guid="Creature-0-1-2-3-1234-00000001"; messages={};hooks={};SlashCmdList={}; log={}
function GetTime() return clock end
function time() return 1700000000+math.floor(clock) end
function UnitExists() return target end
function UnitGUID() return target and guid or nil end
function UnitHealth() return hp end
function UnitHealthMax() return maximum end
function UnitIsPlayer() return player end
function UnitIsUnit() return false end
function UnitInParty() return party end
function UnitInRaid() return false end
function UnitLevel() return 10 end
function UnitClassification() return "normal" end
function print(text) messages[#messages+1]=text end
function text() return {SetText=function(self,t) self.text=t end,Show=function(self) self.shown=true end} end
TargetFrameHealthBar={TextString=text(),LeftText=text(),RightText=text()}
function TextStatusBar_UpdateTextStringWithValues() end
function hooksecurefunc(name,fn) hooks[name]=fn end
function CreateFrame() frame={RegisterEvent=function()end,SetScript=function(self,k,fn) self[k]=fn end};return frame end
function fire(event,unit) frame.OnEvent(frame,event,unit) end
function advance(seconds) clock=clock+seconds;frame.OnUpdate(frame,seconds) end
function CombatLogGetCurrentEventInfo() return unpack(log) end
function combat(event,amount,overkill,dest,source)
 log={clock,event,false,source or "Player-0-ALLY","attacker",0,0,dest or guid,"target",0,0}
 if event=="SWING_DAMAGE" then
  log[12]=amount;log[13]=overkill or -1;log[14]=1;log[15]=0;log[16]=0;log[17]=0
 elseif event=="ENVIRONMENTAL_DAMAGE" then
  log[12]="FALLING";log[13]=amount;log[14]=overkill or -1
 elseif event=="SPELL_HEAL" or event=="SPELL_PERIODIC_HEAL" then
  log[12]=123;log[13]="Heal";log[14]=1;log[15]=amount;log[16]=0
 else
  log[12]=123;log[13]="Spell";log[14]=1;log[15]=amount;log[16]=overkill or -1
 end
 fire("COMBAT_LOG_EVENT_UNFILTERED")
end
function hit(amount,percent,healthFirst,source,event,overkill)
 clock=clock+.3
 if healthFirst then hp=percent;fire("UNIT_HEALTH","target") end
 combat(event or "SWING_DAMAGE",amount,overkill or -1,nil,source)
 if not healthFirst then hp=percent;fire("UNIT_HEALTH","target") end
 advance(.4)
end
function shown() return TargetFrameHealthBar.TextString.text end
