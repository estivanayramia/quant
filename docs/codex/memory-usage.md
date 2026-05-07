# Codex Memory Usage

Use `codebaseMemory` first for repo structure:

- what calls this function,
- which files participate in replay readiness,
- where lane decisions flow,
- which modules touch prediction-market research and validation.

Use `memoryGraph` only for durable project memory that should survive across sessions:

- experiment results worth remembering,
- phase handoff context,
- rejected-lane reasons,
- important setup decisions,
- recurring failure causes and fixes.

Do not use memory for:

- secrets,
- API keys,
- wallet data,
- live-trading permissions,
- speculative notes that are not yet verified,
- noisy transcript summaries.

Good MemoryGraph memory shape:

```text
Remember as project memory:
Title: Phase 21 rejected lane reason
Type: project
Content: The lane was rejected because ...
Tags: quant, lane-selection, rejected-lane, phase-21
```

MemoryGraph should be intentional, not automatic. If a fact is operationally important,
prefer adding it to tracked docs, tests, or policy files after review.
