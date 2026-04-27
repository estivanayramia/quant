# Autonomous Operations

Phase 2 adds a local autonomous operations control plane for safe modes only:

- local research cycles
- shadow-mode cycles
- paper/dry-run-ready scaffolds
- scheduled reporting
- watchdog health checks
- drift/slippage monitoring
- strategy quarantine workflows
- mock alerts
- AI summaries through mock/support providers

It does not enable live trading. It does not place real orders. It does not require broker keys, exchange keys, Telegram keys, or real AI-provider keys.

## Run Once

```bash
quant-os autonomous run-once
```

Outputs:

- `reports/autonomy/latest_run.json`
- `reports/autonomy/latest_run.md`
- `reports/autonomy/history/*.json`
- `reports/autonomy/history/*.md`

## Daemon

```bash
quant-os autonomous daemon --interval-minutes 60
```

The daemon is local-only, uses a process lock, writes a heartbeat, and can be stopped with:

```bash
quant-os autonomous stop
```

## Safety

Every autonomous cycle starts with config, secrets, and live-trading guards. If a critical safety check fails, the run stops before shadow/paper/dry-run tasks.

This is now autonomous in safe local/shadow/paper/dry-run-ready modes, not live-money autonomous.

