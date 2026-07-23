# Brainiac Context Brief

Brainiac is a local retrieval and maintenance layer for plain-file knowledge vaults. It keeps durable knowledge in ordinary files, builds an incremental SQLite index, and lets an operator retrieve bounded context safely. New Brainiac-managed vaults use the PARA roots `Inbox/`, `Projects/`, `Areas/`, `Resources/`, and `Archive/`; `Brainiac/` is tool-owned state.

The current product focus is inventory, lexical retrieval, routing, duplicate/canonical handling, vault structure, and umbrella-note maintenance. New notes default to `brainiac_role: source`. Umbrellas are explicit navigation notes; they can include concise rules and preferences when those affect later choices.

Do not build a separate derived-memory layer or automatic summary-maintenance workflow. After a material source update, inspect existing umbrella backlinks and propose an umbrella update only if the change affects navigation, categories, status, ratings, or choice rules.
