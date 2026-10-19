# Mob Health Numbers

**For World of Warcraft Classic 1.14.2 (Interface 11402).**

Mob Health Numbers learns NPC health from combat and displays it on the default
target frame and in mouseover tooltips. It saves learned values for future
encounters and can optionally share observations with other users of the addon.

## Install

1. Download `MobHealthNumbers-1.0.0.zip` from Releases and close WoW.
2. Extract the ZIP into your client's `Interface/AddOns` folder.
3. Start WoW and enable **Mob Health Numbers** in the character selection AddOns menu.
4. Type `/mobhp options` to open settings, or `/mobhp help` for commands.

The file should be at `Interface/AddOns/MobHealthNumbers/MobHealthNumbers.toc`.
No additional addons are required. The default target frame and tooltip are
supported; custom unit frames and other client versions are unverified.

## Display

- **Target frame:** current NPC health, such as `1,240`.
- **Mouseover tooltip:** current and maximum health. Calculated values are
  labelled **Estimated health**.
- **Unknown health:** a percentage until enough information is available.

Player and player-pet health displays are not modified. Use tooltip-only mode
if you prefer the normal target-frame text.

## Settings

Open **Interface > AddOns > Mob Health Numbers**, or type `/mobhp options`.

- **Show current HP on the target frame:** turn this off for mouseover details only.
- **Share learned health with other addon users:** guild and party/raid sharing is on by default; turn it off here if preferred.
- **Cache and current target:** live local/peer record counts and limits, the active realm cache, and current target health and its source.
- **Test communications:** send one hidden self-whisper and see the result in the panel. Sharing does not need to be enabled.
- **Restore defaults:** enable target-frame health and sharing; learned records are kept.

Changes apply immediately and are saved between sessions. Mouseover tooltips
show health details in either display mode.
Scroll down for diagnostics and communications. A successful self-whisper test
confirms that route only; guild and party/raid sharing need another user to verify.

## Commands

| Command | Action |
| --- | --- |
| `/mobhp help` | Show help |
| `/mobhp options` or `/mobhp settings` | Open the settings panel |
| `/mobhp` or `/mobhp status` | Show display mode, record counts and target information |
| `/mobhp mode target` | Show target health and mouseover details (default) |
| `/mobhp mode hover` | Show mouseover details only |
| `/mobhp peers on` | Enable sharing with other addon users (default) |
| `/mobhp peers off` | Disable sharing |
| `/mobhp commtest` | Test addon messaging with one hidden whisper to yourself |
| `/mobhp reset` | Show the cache-deletion instructions |
| `/mobhp reset confirm` | Delete this realm's learned and received health records |

## Learning health

Keep an NPC visible and observe it from full health to death. Damage from all
attackers visible in your combat log contributes to learning, with adjustments
for healing and overkill. Select another NPC of the same type and level to use
the learned value. Records persist after reloading the UI or restarting WoW.

Partial fights can produce a live estimate but do not create a completed-fight
record. Early estimates may change as more information becomes available.
Cached maximum health normally stays fixed for the current encounter. Strong,
consistent observations can correct an inaccurate cached value. Learned values
are grouped by realm, creature type, level and classification.

Some legacy realms do not report how much of the killing hit exceeded the NPC's
remaining health. In that case, the addon learns from health changes observed
before the killing hit. Very short fights may not provide enough information
to save a record; the entire killing hit is never assumed to be effective damage.

A visibility gap prevents saving an incomplete fight, but an estimate already
obtained for that NPC remains available during the encounter. An NPC resetting
to full health starts a fresh observation.

## Limitations

Estimated health is calculated, not authoritative server data. Missed combat
messages, visibility gaps, regeneration and unusual encounter mechanics can
affect accuracy. Individual NPCs may also differ from their learned template.
The addon rejects inconsistent observations, so some fights may not add a record.

When the client supplies numeric health, it is displayed directly. A reported
maximum of exactly 100 is treated as percentage-based health.

## Optional sharing

Sharing is **on by default** and can be disabled in settings. An existing saved
choice to disable sharing is preserved when updating. Completed observations can be sent
to guild and party/raid members running a compatible version. Local observations
take priority over received values. Received values expire after 15 minutes
and are not saved between sessions.

Messages contain the realm name, creature ID, level, classification and learned
maximum health; WoW identifies the sender to recipients. The configured login
portal or proxy address is not stored in active cache keys, displayed, or included in shared messages.
Sharing matches by realm name, so users on the same realm can exchange records
when using different proxies. Separate servers with identical realm names are
not distinguished by caching or peer sharing. Messaging support depends on your realm.
A successful `/mobhp commtest` confirms the self-whisper route only.

The addon uses no external service, telemetry or automatic updater. Settings
and learned records are stored locally in WoW's SavedVariables.

## Troubleshooting

If you only see percentages, observe a full fight, check `/mobhp status`, then
select another NPC of the same type and level. A rejected or partial fight may
leave the record count unchanged.

Status includes the active realm cache. Learned records are selected after login
when the realm name is available and remain saved across `/reload`. The local
record count counts creature type/level/classification entries, not individual
kills. Existing records are migrated when updating this addon. Cache keys use realm names
only, so changing a login proxy does not hide your learned records. Older records
for other realms are retained under opaque compatibility fingerprints until that
realm is revisited through its previous endpoint; readable endpoint labels are
removed. These fingerprints are compatibility identifiers, not encrypted secrets.

If target text looks wrong, disable other addons that replace the same health
text, or try `/mobhp mode hover`.

For a bug report, include the addon version, client build, steps to reproduce,
other UI addons and any Lua error. Remove personal details from screenshots
and logs.

## Sharing and removal

You may share and modify this addon under the [MIT license](LICENSE.txt).
Include the license and documentation when sharing the addon folder or ZIP.
Do not include your `WTF` folder, account files or personal logs.

To uninstall, close WoW and remove the `MobHealthNumbers` folder. Saved records
remain available if you reinstall. Use `/mobhp reset confirm` before removal
if you want to clear this realm's health records.

Author: **Mario Debono**. See [CREDITS.md](CREDITS.md).
