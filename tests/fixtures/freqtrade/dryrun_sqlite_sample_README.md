# Synthetic SQLite Fixture Note

Phase 6 tests do not require a real Freqtrade SQLite database. SQLite parser tests create tiny temporary local databases when needed and verify that missing or unreadable files degrade gracefully.
