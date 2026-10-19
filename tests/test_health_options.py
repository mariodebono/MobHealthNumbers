"""Settings controls share the same persistent state and effects as chat commands."""
import test_independent_health as base

UI=r'''
categories={};opened={}
local create=CreateFrame
local function region()
 local r={}
 function r:SetPoint(...) end
 function r:SetWidth(...) end
 function r:SetSize(...) end
 function r:SetColorTexture(...) end
 function r:SetJustifyH(...) end
 function r:SetText(t) self.text=t end
 return r
end
function CreateFrame(kind,name,parent,template)
 local f=create()
 f.name=name;f.parent=parent;f.template=template
 function f:CreateFontString(...) return region() end
 function f:CreateTexture(...) return region() end
 function f:SetPoint(...) end
 function f:SetSize(...) end
 function f:SetText(t) self.text=t end
 function f:SetChecked(v) self.checked=v end
 function f:GetChecked() return self.checked end
 function f:SetEnabled(value) self.enabled=value end
 function f:IsShown() return self.shown==true end
 function f:SetScrollChild(child) self.scrollChild=child end
 function f:Click(value) if self.enabled==false then return end;if value~=nil then self.checked=value end;self.OnClick(self) end
 if name then _G[name]=f end
 return f
end
function InterfaceOptions_AddCategory(p) categories[#categories+1]=p end
function InterfaceOptionsFrame_OpenToCategory(p) opened[#opened+1]=p;p.shown=true;if p.OnShow then p.OnShow(p) end end
'''
saved='MobHealthLearningDB={version=1,realms={["test-TestRealm"]={records={["1234:10:normal"]={hp=1000,seen=1700000000,samples=1,history={1000}}}}}}'
lua=base.new(UI,saved)
base.check(lua,'assert(#categories==1 and categories[1].name=="Mob Health Numbers")')
base.check(lua,'assert(MobHealthNumbersTargetOption:GetChecked()==true and MobHealthNumbersSharingOption:GetChecked()==true)')
base.check(lua,'SlashCmdList.MOBHEALTHNUMBERS("options");assert(#opened==2 and opened[1]==categories[1])')
base.check(lua,'MobHealthNumbersTargetOption:Click(false);assert(MobHealthNumbersSettings.mode=="hover" and shown()=="native")')
base.check(lua,'MobHealthNumbersTargetOption:Click(1);assert(MobHealthNumbersSettings.mode=="target" and shown()=="1,000")')
base.check(lua,'MobHealthNumbersSharingOption:Click(true);assert(MobHealthNumbersSettings.peers==true)')
base.check(lua,'SlashCmdList.MOBHEALTHNUMBERS("peers off");assert(MobHealthNumbersSharingOption:GetChecked()==false and MobHealthNumbersSettings.peers==false)')
base.check(lua,'SlashCmdList.MOBHEALTHNUMBERS("mode hover");assert(MobHealthNumbersTargetOption:GetChecked()==false)')
base.check(lua,'SlashCmdList.MOBHEALTHNUMBERS("settings");assert(#opened==4 and MobHealthNumbersTargetOption:GetChecked()==false)')
base.check(lua,'MobHealthNumbersSharingOption:Click(false);MobHealthNumbersDefaultsOption:Click();assert(MobHealthNumbersSettings.mode=="target" and MobHealthNumbersSettings.peers==true and records()["1234:10:normal"].hp==1000)')
base.check(lua,'assert(MobHealthNumbersTargetOption:GetChecked()==true and MobHealthNumbersSharingOption:GetChecked()==true)')
lua=base.new(UI+'MobHealthNumbersSettings={mode="hover",peers=true}')
base.check(lua,'assert(MobHealthNumbersTargetOption:GetChecked()==false and MobHealthNumbersSharingOption:GetChecked()==true)')
base.check(lua,'SlashCmdList.MOBHEALTHNUMBERS("options");assert(MobHealthNumbersSettings.mode=="hover" and MobHealthNumbersSettings.peers==true)')
lua=base.new()
base.check(lua,'SlashCmdList.MOBHEALTHNUMBERS("options");assert(messages[#messages]:find("panel unavailable",1,true))')

lua=base.new(UI+'MobHealthNumbersSettings={peers=false}')
base.check(lua,'assert(MobHealthNumbersSettings.peers==false and MobHealthNumbersSharingOption:GetChecked()==false)')
lua=base.new(UI+'MobHealthNumbersSettings={mode="hover"}')
base.check(lua,'assert(MobHealthNumbersSettings.peers==true and MobHealthNumbersSharingOption:GetChecked()==true and MobHealthNumbersSettings.mode=="hover")')
lua=base.new('isGuild=true')
base.check(lua,'dead(1000);advance(2);assert(MobHealthNumbersSettings.peers==true and #outgoing==1 and outgoing[1][3]=="GUILD")')

lua=base.new(UI,saved)
base.check(lua,'SlashCmdList.MOBHEALTHNUMBERS("options");local p=MobHealthNumbersOptionsPanel;'
    'assert(p.localCount.text=="1 / 4,096" and p.peerCount.text=="0 / 1,024");'
    'assert(p.realmText.text=="TestRealm" and p.targetText.text=="1,000 / 1,000 HP (learned)")')
base.check(lua,'local n=#messages;advance(2);assert(#messages==n)')
base.check(lua,'selectMob(5678);dead(2000);advance(.6);assert(MobHealthNumbersOptionsPanel.localCount.text=="2 / 4,096")')
base.check(lua,'MobHealthNumbersSharingOption:Click(true);'
    'fire("CHAT_MSG_ADDON","MHN114v1","H|TestRealm|9999:10:normal|2500","GUILD","Friend");'
    'advance(.6);assert(MobHealthNumbersOptionsPanel.peerCount.text=="1 / 1,024")')
base.check(lua,'selectMob(9999);advance(.6);assert(MobHealthNumbersOptionsPanel.targetText.text=="2,500 / 2,500 HP (received)")')
base.check(lua,'MobHealthNumbersSharingOption:Click(false);MobHealthNumbersCommTestOption:Click();'
    'assert(MobHealthLearning.GetStatus().commState=="pending" and MobHealthNumbersCommTestOption.enabled==false);'
    'assert(#outgoing==1 and outgoing[1][3]=="WHISPER" and MobHealthNumbersSettings.peers==false)')
base.check(lua,'MobHealthNumbersCommTestOption:Click();assert(#outgoing==1)')
base.check(lua,'fire("CHAT_MSG_ADDON","MHN114v1",outgoing[1][2],"WHISPER","Other");'
    'assert(MobHealthLearning.GetStatus().commState=="pending")')
base.check(lua,'fire("CHAT_MSG_ADDON","MHN114v1",outgoing[1][2],"WHISPER","Tester-TestRealm");advance(.6);'
    'assert(MobHealthLearning.GetStatus().commState=="success" and MobHealthNumbersCommTestOption.enabled==true);'
    'assert(MobHealthNumbersOptionsPanel.testResult.text:find("Self-whisper received",1,true))')
base.check(lua,'MobHealthNumbersCommTestOption:Click();advance(6);'
    'assert(MobHealthLearning.GetStatus().commState=="timeout" and MobHealthNumbersCommTestOption.enabled==true);'
    'assert(MobHealthNumbersOptionsPanel.testResult.text:find("No reply received",1,true))')
base.check(lua,'C_ChatInfo.SendAddonMessage=nil;MobHealthNumbersCommTestOption:Click();'
    'assert(MobHealthLearning.GetStatus().commState=="unavailable" and MobHealthNumbersCommTestOption.enabled==true)')
base.check(lua,'C_ChatInfo.SendAddonMessage=function() error("routing unavailable") end;MobHealthNumbersCommTestOption:Click();'
    'assert(MobHealthLearning.GetStatus().commState=="error" and MobHealthNumbersCommTestOption.enabled==true)')
base.check(lua,'target=false;advance(.6);'
    'assert(MobHealthNumbersOptionsPanel.targetText.text=="Select an NPC to see its health source.")')
base.check(lua,'MobHealthNumbersOptionsPanel.shown=false;local previous=MobHealthLearning.GetStatus;local calls=0;'
    'MobHealthLearning.GetStatus=function() calls=calls+1;return previous() end;advance(2);assert(calls==0)')

lua=base.new(UI+'realm=""',enter_world=False)
base.check(lua,'SlashCmdList.MOBHEALTHNUMBERS("options");'
    'assert(MobHealthNumbersOptionsPanel.realmText.text=="Waiting for realm information...")')
base.check(lua,'MobHealthNumbersCommTestOption:Click();'
    'fire("CHAT_MSG_ADDON","MHN114v1",outgoing[1][2],"WHISPER","Tester");advance(.6);'
    'assert(MobHealthLearning.GetStatus().commState=="success" and MobHealthNumbersCommTestOption.enabled==true)')
base.check(lua,'MobHealthNumbersCommTestOption:Click();advance(6);'
    'assert(MobHealthLearning.GetStatus().commState=="timeout" and MobHealthNumbersCommTestOption.enabled==true)')
print(f'PASS: {base.checks} total checks including settings registration, UI/chat synchronization, persisted values and safe defaults')
