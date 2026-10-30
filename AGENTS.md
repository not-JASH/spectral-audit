# Project guidance

Read `docs/RESEARCH_PROTOCOL.md`, `docs/ENGINEERING_SPEC.md`, and
`docs/ACCEPTANCE_CRITERIA.md` before changing measurement behavior. Preserve
units, estimands, endpoint rules, denominators, and truthful unavailable states.
Record actual research and development history; do not claim unrun results.
Test meaningful numerical changes with `python -m pytest -q` and lint with
`python -m ruff check .`. Keep future milestones separate from M0.
