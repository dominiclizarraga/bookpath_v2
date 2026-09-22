# AGENTS.md

## Project Overview

BookPath is a Python ML application that recommends books based on a user's
learning goal and experience level. Aim for clean architecture, reproducibility,
meaningful evaluation, and maintainability.

## Engineering Principles

- Follow Python conventions and PEP 8; use clear, intention-revealing names.
- Give each function, class, and module one clear responsibility.
- Prefer small classes and methods. Aim for classes under 100 lines and methods
  under 5 logical lines, but prioritize coherent, readable code over line counts.
- Keep dependencies explicit, interfaces small, and entry points thin.
- Separate data access, transformations, ML logic, and presentation.
- Avoid abstractions and functionality for hypothetical future requirements.

When principles conflict, prioritize:
correctness > tests > readability > simplicity > design rules.

## Development

Use `uv` for Python environments and dependencies:

```sh
uv sync                    # Install project dependencies
uv run pytest              # Run tests
uv run python -m <module>  # Run a module
uv add <package>            # Add a runtime dependency
uv add --dev <package>      # Add a development dependency
```

Keep dependency declarations and the lockfile in sync; avoid direct `pip install`.

## Testing

- Use pytest and follow red-green-refactor when practical.
- Test observable behavior; include regression tests for bug fixes when practical.
- Mock external boundaries, not internal methods merely to make tests pass.
- Keep tests deterministic and independent of live external services.
- Run relevant tests for code changes and report what was actually verified.

## ML and Data

- Keep notebooks exploratory and reusable logic in the package.
- Preserve raw data and keep transformations traceable and reproducible.
- Reuse saved datasets during exploration; refresh external data explicitly.
- Keep data access separate from preprocessing and evaluation from inference.
- Prevent evaluation leakage; fit learned preprocessing on training data only.
- Record seeds and configuration where they affect results.
- Assess changes to preprocessing, models, and ranking against relevant metrics.

## Security

- Never commit secrets, credentials, or `.env` files, or log sensitive values.
- Read secrets from environment variables or approved secret-management systems.
- Validate untrusted inputs and use least-privilege access to external services.

## Collaboration and Reviews

- Keep changes focused; explain decisions and tradeoffs in plain language.
- For reviews, report evidence, file locations, consequences, and suggested fixes.
- Separate bugs from optional conventions; implement review fixes when requested.
- Keep detailed software, ML-engineering, and statistical checks in focused skills.
- Do not stage, commit, or push unless requested.
