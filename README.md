# Gated CI Pipeline — Todo API

A deliberately tiny FastAPI + pytest todo API, built as the vehicle for
a CI activity. The point isn't the app — it's that **broken code
physically cannot reach `main`** once the pipeline and branch
protection are set up.

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then edit .env with a real local value
export $(cat .env | xargs)       # or use a tool like direnv

uvicorn app.main:app --reload
pytest -v
```

## Branch strategy

```
feature/* ──▶ dev ──▶ staging ──▶ main
    |          |          |         |
    |          |          |         └── production. protected. tagged releases.
    |          |          └── pre-prod. mirrors production config.
    |          └── integration. where features meet each other.
    └── short-lived. one branch = one unit of work.
```

- **`feature/*`** — one branch per unit of work. Branched from `dev`,
  merged back into `dev`, then deleted.
- **`dev`** — where features integrate with each other first.
- **`staging`** — mirrors production config; last stop before release.
- **`main`** — production. Protected. Every merge here should be
  tagged as a release.

## Commit discipline

[Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add recipe search endpoint
fix: handle empty query string in search
test: add coverage for search edge cases
ci: run tests on pull requests to dev
docs: document required environment variables
```

## Secrets management

Three separate things, kept separate on purpose:

| # | What | Where |
|---|------|-------|
| a | Never commit secrets | `.env` is git-ignored; only `.env.example` (placeholder values) is committed |
| b | Real values | GitHub → repo → Settings → Secrets and variables → Actions → `ADMIN_API_KEY` (a fake value is fine for this activity) |
| c | Proof it isn't leaked | The "Prove the secret is usable but not leaked" step in `.github/workflows/ci.yml` — it checks the secret is present without ever printing it, and GitHub auto-masks the raw value in logs regardless |
| d | Scan history for leaked secrets | The `gitleaks` step in CI, run on every push/PR |

The app itself needs this secret for a real reason: `DELETE /todos`
(bulk wipe) requires an `X-Admin-Key` header matching `ADMIN_API_KEY`,
or it returns `403`.

## The CI workflow

`.github/workflows/ci.yml` runs on every push and pull request into
`dev`, `staging`, or `main`. It installs dependencies, runs the pytest
suite, checks the secret is wired up correctly, and scans for
committed secrets with gitleaks. **This job is the gate** — see branch
protection below for how it becomes a blocking gate rather than a
decorative badge.

## Branch protection — setting up the gate

This part happens in GitHub's UI (or via `gh` / the API), not in code:

1. Push this repo to GitHub and let the first CI run complete once
   (GitHub needs to see the `test` job run at least once before you
   can require it).
2. Go to **Settings → Branches → Add branch protection rule**.
3. Branch name pattern: `main` (repeat later for `staging` and `dev`
   if you want them gated too).
4. Enable:
   - **Require a pull request before merging**
   - **Require status checks to pass before merging** → search for
     and select **`test`**
   - **Require branches to be up to date before merging**
   - **Do not allow bypassing the above settings** (include
     administrators — otherwise you can quietly override your own
     gate)
5. Save.

At this point, a PR into `main` with a failing `test` job shows a red
X and GitHub disables the merge button. That's the gate.

## Proving the gate works

1. Create a feature branch and deliberately break something, e.g.
   change an assertion in `tests/test_main.py` so it's wrong.
2. Push it and open a PR into `dev` (or `main`, once protection is on
   there).
3. Watch the `CI` check turn red and the **Merge** button gray out —
   screenshot this, it's your proof the gate blocks broken code.
4. Fix the code, push again, watch the check turn green, and merge.
5. Read the failed run's log (Actions tab → the failed run → the
   `test` step) to confirm you can trace a red X back to the actual
   failing assertion, not just that it failed.
