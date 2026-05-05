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

Phase 13 treats stoploss-on-exchange support as a hard gate. Unknown or false
adapter capability blocks fire attempts, including tiny canary attempts.

Phase 14 extends that hard gate to the single real-adapter path. The real
adapter is blocked unless its local settings explicitly document
`stoploss_on_exchange_supported: true`. Unknown support, missing settings, or
unsupported stoploss capability keeps live fire blocked.
