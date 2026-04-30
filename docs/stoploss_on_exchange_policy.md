# Stoploss-On-Exchange Proof Policy

Phase 12 designs the evidence that a future canary would need before any live
order could be considered. It does not connect to an exchange and does not
place a stoploss order.

Future proof must show that the selected exchange and adapter support native
protective stop orders for the selected spot pair, that the protective order is
acknowledged before an entry is considered protected, and that the stoploss can
be reconciled after reconnect or restart.

Until that proof exists, canary rehearsal and final gate reports must keep live
blocked.
