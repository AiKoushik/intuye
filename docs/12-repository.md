# Repository setup

How the GitHub repository is configured, so it can be rebuilt or checked. Contributors only need
[CONTRIBUTING.md](../CONTRIBUTING.md).

## Branches and rules

`main` holds released code, `develop` is where work lands, and everything else is a short-lived branch.
The rules are kept as files in [`.github/rulesets/`](../.github/rulesets/) so they're reviewed like code.

| Ruleset | Applies to | What it enforces |
|---|---|---|
| `main.json` | `main` | Pull request required, merge commits only, all four CI checks, branch up to date, conversations resolved, no force pushes or deletion |
| `develop.json` | `develop` | Pull request required, squash merges only, linear history, three CI checks, conversations resolved, no force pushes or deletion |
| `release-tags.json` | `v*` tags | Tags can't be moved or deleted |

Repository admins can bypass a rule only by merging a pull request (for example when a check is down),
never by pushing directly. Approvals are set to zero while there's one maintainer, since GitHub doesn't
let you approve your own pull request. Raise `required_approving_review_count` to 1 and turn on
`require_code_owner_review` when a second maintainer joins.

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on every pull request and on pushes to `main` and `develop`.

| Check | What it runs |
|---|---|
| Backend tests | `pytest` in `backend/` on Python 3.12 |
| Web build | `node --check` on every web module |
| Design tokens | `design/tokens/generate.py --check`, then fails if the generated files differ from what's committed |
| Web end to end | `scripts/e2e.sh` with Playwright against a fresh backend. Screenshots are uploaded when it fails. |

Dependabot ([`.github/dependabot.yml`](../.github/dependabot.yml)) opens update pull requests against `develop`.

## Applying the settings

GitHub settings can't be changed from inside the repository, so they're applied once by the owner.

**With the GitHub CLI** (signed in as the owner), from the repository folder

```powershell
.\scripts\github-setup.ps1
```

```bash
scripts/github-setup.sh
```

The script imports the three rulesets, makes `develop` the default branch for new pull requests, sets
the merge options and turns on the security features listed below. It's safe to run again, since it replaces
rulesets with the same name.

**By hand**, in the repository's Settings

1. Rules, Rulesets, New ruleset, Import a ruleset. Import `main.json`, `develop.json` and `release-tags.json` one at a time.
2. General, Default branch. Switch to `develop`.
3. General, Pull Requests. Allow merge commits and squash merging, turn off rebase merging, set squash
   commits to default to the pull request title, and turn on automatically deleting head branches and
   always suggesting to update pull request branches.
4. Code security. Turn on private vulnerability reporting, Dependabot alerts and security updates, and
   secret scanning with push protection.
5. Actions, General. Leave workflow permissions at read-only.
