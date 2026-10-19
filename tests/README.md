# Mob Health Numbers tests

Run `python tests/test_mob_health.py` from the repository root after installing
`requirements-dev.txt`. Python and Lupa with Lua 5.1 support are required.

The suite checks combat accounting, healing and overkill, event ordering,
partial fights, percentage rounding, missed observations, cache persistence,
realm separation, display modes, tooltips, player exclusion, peer messaging and
settings controls, including saved preferences and UI/chat synchronization.
Peer checks exchange an actual message between simulated clients using different
proxies, verify realm-only payloads, and use realm-only persistent caches across proxies. Migration checks preserve
legacy records while removing readable endpoint labels.
Settings diagnostics cover live record counts, target changes, quiet refreshes,
and self-whisper tests with success, timeout, missing API and send-error results.
It includes 40 simulated fights with multiple attackers and healing.

Regression coverage includes a full saved-data reload with delayed realm
availability, realm isolation, unavailable killing-hit overkill, death arriving
before the final hit, zero-overkill shield hits, and retaining numeric estimates
through visibility gaps. Another 40 fights combine integer-rounded percentages,
multiple attackers, healing and unknown overkill, checking the inferred maximum
against an independent health model with a 3% rounding tolerance.
Conflicting old cache values are corrected only by consistent observations;
missed damage cannot replace a record with a contradictory estimate.

These tests use mocked WoW APIs. In-game testing is also needed to verify
client behavior and your realm's addon messaging support.
