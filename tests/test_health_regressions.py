"""Reload timing and legacy-proxy combat regressions, using the real addon files."""
import random
import test_health_options as options

base = options.base
failures = []


def check(name, lua, code):
    try:
        base.check(lua, code)
    except Exception as error:
        failures.append(name)
        print(f'FAIL: {name}: {error}')


saved = options.saved
lua = base.new('function GetAddOnMetadata(name,field) '
               'if name=="MobHealthNumbers" and field=="Version" then return "9.8.7" end end')
check('displayed version comes from addon metadata', lua,
      'assert(MobHealthLearning.Version=="9.8.7");MobHealthLearning.Status();'
      'assert(messages[#messages-1]:find("9.8.7",1,true));'
      'SlashCmdList.MOBHEALTHNUMBERS("help");'
      'local found=false;for _,message in ipairs(messages) do '
      'if message:find("9.8.7 -",1,true) then found=true end end;assert(found)')
lua = base.new('realm=""', saved, enter_world=False)
check('no unnamed realm cache during loading', lua,
      'assert(MobHealthLearningDB.realms["test-"]==nil)')
check('saved realm selected after login', lua,
      'realm="TestRealm";fire("PLAYER_LOGIN");fire("PLAYER_ENTERING_WORLD");advance(.3);'
      'local h,m,s=MobHealthLearning.GetHealth("target");assert(h==1000 and m==1000 and s=="learned");'
      'MobHealthLearning.Status();assert(messages[#messages-1]:find("Local records 1",1,true))')
check('world transitions keep saved records', lua,
      'local previous=records();fire("PLAYER_ENTERING_WORLD");advance(.3);'
      'assert(records()==previous and records()["1234:10:normal"].hp==1000)')

lua = base.new('realm=""', saved)
check('late realm availability retried after world entry', lua,
      'realm="TestRealm";advance(.5);local h,m=MobHealthLearning.GetHealth("target");'
      'assert(h==1000 and m==1000 and MobHealthLearningDB.realms["test-"]==nil)')

lua = base.new('function GetRealmName() return realm end;'
               'function GetNormalizedRealmName() return "" end', saved)
check('empty normalized realm falls back to realm name', lua,
      'local h,m=MobHealthLearning.GetHealth("target");assert(h==1000 and m==1000)')

lua = base.new(saved=saved)
check('realm changes remain isolated', lua,
      'realm="OtherRealm";fire("PLAYER_ENTERING_WORLD");advance(.3);'
      'local h=MobHealthLearning.GetHealth("target");assert(h==nil and next(records())==nil);'
      'realm="TestRealm";fire("PLAYER_ENTERING_WORLD");advance(.3);'
      'assert(records()["1234:10:normal"].hp==1000)')

# Serialize and load a learned database in a NEW Lua VM, with no realm initially
# available. This exercises persistence instead of reusing an in-memory table.
lua = base.new()
lua.execute('hit(200,80);hit(300,50);dead(500)')
serialized = lua.eval(r'''function()
 local function encode(value)
  if type(value)=="table" then
   local items={"{"};for key,item in pairs(value) do
    items[#items+1]="["..encode(key).."]="..encode(item).."," end
   items[#items+1]="}";return table.concat(items)
  elseif type(value)=="string" then return string.format("%q",value)
  else return tostring(value) end
 end
 return "MobHealthLearningDB="..encode(MobHealthLearningDB)
end''')()
lua = base.new('realm=""', serialized, enter_world=False)
check('learned record survives full reload with delayed realm', lua,
      'realm="TestRealm";fire("PLAYER_ENTERING_WORLD");advance(.3);'
      'local h,m=MobHealthLearning.GetHealth("target");assert(h==1000 and m==1000);'
      'assert(records()["1234:10:normal"].samples==1)')

# The proxy supplies -1 even for a lethal melee/spell hit. Actual remaining
# health is 500 here; a 700-point finishing hit contains 200 unknown overkill.
for kind in ('SWING_DAMAGE', 'SPELL_DAMAGE', 'SPELL_PERIODIC_DAMAGE', 'RANGE_DAMAGE'):
    for death_first in (False, True):
        lua = base.new()
        death = 'combat("UNIT_DIED");advance(.3);' if death_first else ''
        check(f'unknown overkill: {kind}, death first={death_first}', lua,
              'hit(200,80);hit(300,50);' + death +
              f'combat("{kind}",700,-1);hp=0;fire("UNIT_HEALTH","target");'
              'combat("UNIT_DIED");advance(1);selectMob(1234);'
              'assert(records()["1234:10:normal"].hp==1000 and shown()=="1,000")')

lua = base.new()
check('fast kill without overkill does not save inflated damage total', lua,
      'combat("SWING_DAMAGE",400,-1);hp=60;fire("UNIT_HEALTH","target");clock=clock+.1;'
      'combat("SWING_DAMAGE",800,-1);hp=0;fire("UNIT_HEALTH","target");'
      'combat("UNIT_DIED");advance(1);assert(next(records())==nil)')

lua = base.new()
check('nonlethal zero-overkill shield hit keeps live HP', lua,
      'hit(100,90);combat("DAMAGE_SHIELD",10,0);hp=89;fire("UNIT_HEALTH","target");advance(1);'
      'local h,m=MobHealthLearning.GetHealth("target");assert(h==890 and m==1000);'
      'assert(next(records())==nil)')
check('shield hit does not interrupt later learning', lua,
      'hit(390,50);combat("SWING_DAMAGE",700,-1);hp=0;fire("UNIT_HEALTH","target");'
      'combat("UNIT_DIED");advance(1);assert(records()["1234:10:normal"].hp==1000)')

lua = base.new()
check('lethal legacy shield hit does not imply exact zero overkill', lua,
      'hit(200,80);hit(300,50);combat("DAMAGE_SHIELD",700,0);hp=0;'
      'fire("UNIT_HEALTH","target");combat("UNIT_DIED");advance(1);'
      'assert(records()["1234:10:normal"].hp==1000)')

lua = base.new()
check('single shield killing blow without observations is not learned', lua,
      'combat("DAMAGE_SHIELD",1200,0);hp=0;fire("UNIT_HEALTH","target");'
      'combat("UNIT_DIED");advance(1);assert(next(records())==nil)')

lua = base.new()
check('target visibility gap keeps an existing live estimate', lua,
      'hit(200,80);hit(300,50);target=false;advance(4);target=true;'
      'fire("PLAYER_TARGET_CHANGED");advance(.3);local h,m=MobHealthLearning.GetHealth("target");'
      'assert(h==500 and m==1000 and shown()=="500")')
check('incomplete observation is still excluded from persistent learning', lua,
      'hit(100,40);dead(400);assert(next(records())==nil)')

lua = base.new()
check('missed damage is rejected with unknown-overkill killing blow', lua,
      'hit(100,50);hit(100,40);combat("SWING_DAMAGE",600,-1);hp=0;'
      'fire("UNIT_HEALTH","target");combat("UNIT_DIED");advance(1);assert(next(records())==nil)')

bad_saved = 'MobHealthLearningDB={version=1,realms={["test-TestRealm"]={records={' \
            '["1234:10:normal"]={hp=46,seen=1700000000,samples=1,history={46}}}}}}'
lua = base.new(saved=bad_saved)
check('consistent observations supersede an obviously wrong cached maximum', lua,
      'hit(200,80);hit(300,50);local h,m,s=MobHealthLearning.GetHealth("target");'
      'assert(h==500 and m==1000 and s=="live")')
check('completed fight replaces contradicted history instead of averaging it', lua,
      'combat("SWING_DAMAGE",700,-1);hp=0;fire("UNIT_HEALTH","target");'
      'combat("UNIT_DIED");advance(1);local r=records()["1234:10:normal"];'
      'assert(r.hp==1000 and #r.history==1 and r.history[1]==1000)')
check('next mob uses the corrected persisted record', lua,
      'selectMob(1234);assert(shown()=="1,000")')

lua = base.new(saved=bad_saved)
check('inconsistent observations cannot overwrite cached health', lua,
      'hit(100,50);hit(100,40);local _,m=MobHealthLearning.GetHealth("target");'
      'assert(m==46 and records()["1234:10:normal"].hp==46)')

# Quantized percentages, multiple attackers, healing and an unknown finishing
# overkill are all present together. Validate against independently maintained
# remaining HP, allowing 3% error from integer percentages rather than treating
# inferred health as authoritative. Alternate floor and nearest rounding.
randomizer = random.Random(11403)
for case in range(40):
    lua = base.new()
    maximum = randomizer.randint(150, 1000000)
    remaining = maximum
    for step in range(8):
        amount = min(remaining - 1, max(1, int(maximum * randomizer.uniform(.04, .08))))
        remaining -= amount
        percent = int(100 * remaining / maximum + (.5 if case % 2 else 0))
        lua.execute(f'hit({amount},{percent},{"true" if step % 2 else "false"},"Player-0-{step % 3}")')
        if step in (3, 5):
            effective = max(1, int((maximum - remaining) * .1))
            remaining += effective
            percent = int(100 * remaining / maximum + (.5 if case % 2 else 0))
            lua.execute(f'combat("SPELL_HEAL",{effective});hp={percent};fire("UNIT_HEALTH","target");advance(.4)')
    overkill = randomizer.randint(maximum // 4, maximum)
    check(f'rounded proxy fight {case}', lua,
          f'combat("SWING_DAMAGE",{remaining + overkill},-1);hp=0;fire("UNIT_HEALTH","target");'
          'combat("UNIT_DIED");advance(1);local r=records()["1234:10:normal"];'
          f'assert(r and math.abs(r.hp-{maximum})/{maximum}<=.03)')

if failures:
    raise AssertionError(f'{len(failures)} regression cases failed: {", ".join(failures)}')
# Endpoint-free caches migrate across proxies, merge by newest observation,
# preserve other realms, and survive serialization without readable endpoints.
legacy = 'MobHealthLearningDB={version=1,realms={' \
    '["192_0_2_10_1119-TestRealm"]={records={["1234:10:normal"]={hp=1000,seen=1700000000}}},' \
    '["old-proxy-TestRealm"]={records={["1234:10:normal"]={hp=1200,seen=1699999999},["5678:10:normal"]={hp=2000,seen=1700000000}}},' \
    '["192_0_2_10_1119-OtherRealm"]={records={["9999:10:normal"]={hp=3000,seen=1700000000}}}}}'
lua = base.new('portal="192.0.2.10:1119"',legacy)
check('migration merges proxy caches and keeps newest duplicate',lua,
      'assert(records()["1234:10:normal"].hp==1000 and records()["5678:10:normal"].hp==2000)')
check('active cache and status contain realm only',lua,
      'assert(MobHealthLearningDB.version==2 and MobHealthLearning.GetStatus().scope=="TestRealm");'
      'for key in pairs(MobHealthLearningDB.realms) do assert(key=="TestRealm") end;'
      'for key in pairs(MobHealthLearningDB.legacy) do assert(#key==16 and not key:find("192_0_2",1,true)) end')
check('proxy changes keep the same learned cache',lua,
      'portal="different-proxy";fire("PLAYER_ENTERING_WORLD");assert(records()["1234:10:normal"].hp==1000)')
check('other legacy realm is recoverable without retaining its endpoint label',lua,
      'portal="192.0.2.10:1119";realm="OtherRealm";fire("PLAYER_ENTERING_WORLD");'
      'assert(records()["9999:10:normal"].hp==3000 and next(MobHealthLearningDB.legacy)==nil)')
lua = base.new('function GetCVar() error("fresh database must not read endpoint") end')
check('fresh database never needs portal configuration',lua,
      'dead(1000);assert(records()["1234:10:normal"].hp==1000 and MobHealthLearning.GetStatus().scope=="TestRealm")')
lua = base.new('realm="Test-Realm"','MobHealthLearningDB={version=1,realms={["old-proxy-Test-Realm"]={records={["1234:10:normal"]={hp=1000,seen=1700000000}}}}}')
check('realm names containing hyphens migrate without splitting their names',lua,
      'assert(records()["1234:10:normal"].hp==1000 and MobHealthLearning.GetStatus().scope=="Test-Realm")')
lua = base.new('realm=""',legacy,enter_world=False)
check('migration waits for a realm and preserves original data during loading',lua,
      'assert(MobHealthLearningDB.version==1);realm="TestRealm";fire("PLAYER_LOGIN");'
      'assert(MobHealthLearningDB.version==2 and records()["1234:10:normal"].hp==1000)')

print(f'PASS: {base.checks} total checks including delayed realm binding, full reload, '
      'legacy unknown overkill, shield hits, stable live HP and 40 rounded proxy fights')
