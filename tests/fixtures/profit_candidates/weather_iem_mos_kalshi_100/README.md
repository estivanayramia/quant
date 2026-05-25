# Weather IEM MOS Kalshi 100 Proof Fixture

This tracked fixture is a sanitized replay fixture for reproducing the Phase 55 weather paper candidate in clean worktrees. It keeps only schema-level proof rows and safety/provenance metadata. It excludes raw captures, secrets, API keys, secret key material, cookies, account data, balances, portfolio data, signed headers, authenticated endpoints, and executable order submission data.

Regenerate reports with:

```powershell
python -m quant_os.cli proving regenerate-profit-candidate-artifacts
```
