# FinSight AI — Project Workflow

## Phase-Based Development Process

FinSight AI is deliberately built in strict, sequential phases, each with a locked scope so later phases can build on a stable, tested foundation instead of a constantly-shifting one.

```
Phase 1: Foundation
  → config, logging, exceptions, constants, helper/utils, database layer, schema
Phase 2: Authentication & User Management
  → registration, login, sessions, RBAC, password reset, profile
Phase 3: Database Services & CRUD
  → full service layer for every table, pagination/filter/search/sort
Phase 4+: Feature Modules
  → dashboard, stock search, analytics, prediction, portfolio, watchlist,
    news, reports, admin (each following the same layered pattern)
```

## Rules That Keep Phases Independent

1. **No silent rewrites.** A completed phase's files are never regenerated in a later phase — only additive changes (new files, or explicitly-called-out extensions like the Phase 2 `password_reset_tokens`/`login_history` tables) are allowed.
2. **Every addition is justified in writing.** Schema/model additions include an inline comment or docs note explaining why the earlier phase's design couldn't accommodate the new requirement.
3. **Each phase ends in a runnable state.** After Phase 1, `database/init_db.py` could create tables. After Phase 2, `streamlit run app.py` could register/log in/reset a password. After Phase 3, every table had a full CRUD service. The project is never left in a broken intermediate state between phases.
4. **Documentation ships with the phase**, not after it — `docs/` is updated as part of the same phase that introduces the behavior it describes.

## Definition of Done (per phase)

- [ ] All files listed in the phase's scope are generated, complete, with no placeholders or `TODO`s
- [ ] Every new `.py` file parses without syntax errors
- [ ] No import cycles introduced (see `docs/coding_standards.md` layering rules)
- [ ] Any schema change has a matching entry in `database/schema.sql` and a standalone migration file
- [ ] `docs/` updated to reflect new architecture/behavior
- [ ] A short "Ready for Phase N+1" summary is provided, including a manual testing checklist

## Current Status

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Foundation | ✅ Complete |
| 2 | Authentication | ✅ Complete |
| 3 | Database Services & CRUD | ✅ Complete |
| 4 | Dashboard & Stock Search | 🔜 Next |
