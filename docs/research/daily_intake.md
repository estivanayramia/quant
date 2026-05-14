# Daily Research Intake

Phase 35 adds a governed local research-intake runner. It is operator-controlled and
does not run as a hidden daemon.

Run it from the repo root on Windows:

```powershell
python .\scripts\research\run_daily_intake.py
```

The runner evaluates `configs/research_intake_sources.yaml`, loads only approved
local captures or cached artifacts by default, dedupes by stable hash, updates the
social hypothesis/task/evidence reports, maps tasks to shadow-proving blockers, and
refreshes the autonomy milestone ledger.

Network fetch is disabled by default. Public/manual sources must be explicitly
approved in source policy and still must not use login-wall scraping, paywall
bypass, CAPTCHA handling, proxy evasion, or any anti-bot workaround. Social or
web research remains hypothesis generation only; it is never a trade signal or
execution trigger.
