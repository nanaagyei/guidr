<!--
  Target `main` from a feature branch (e.g. off `release/dev`).
  PR titles & commits should follow Conventional Commits — release-please uses
  them to compute the next version:
    feat:     -> minor (0.X.0)
    fix:      -> patch (0.0.X)
    feat!/BREAKING CHANGE -> major (X.0.0 once >= 1.0.0)
    chore/docs/test/ci -> no release bump
-->

## What & why

<!-- Brief description of the change and the motivation. -->

## Type of change

- [ ] feat — new user-facing capability
- [ ] fix — bug fix
- [ ] refactor / perf
- [ ] docs / chore / ci
- [ ] breaking change

## Checklist

- [ ] Conventional commit title (`type(scope): summary`)
- [ ] CHANGELOG updated (per-package) if user-facing
- [ ] Tests / typecheck / lint pass locally (`pre-commit run --all-files`)
- [ ] No secrets, keys, or `.env` files committed

## Screenshots / notes

<!-- Optional: UI screenshots, deploy notes, follow-ups. -->
