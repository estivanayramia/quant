# ADR-001: Hexagonal Modular Monolith

The system starts as a modular monolith with ports and adapters. This keeps local execution simple while protecting domain logic from framework, broker, database, and AI-provider coupling.

