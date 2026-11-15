# Contributing to Intuye

Thanks for helping. Here's how the repository works.

## Branches

| Branch | What it's for | How changes get in |
|---|---|---|
| `main` | Released code. Every commit here is something that shipped or is about to. | Pull requests from `release/*` or `hotfix/*` only, merged with a merge commit |
| `develop` | The integration branch. New work lands here first. | Pull requests from your branch, squash merged |
| `feature/<short-name>` | A new feature | Branch from `develop`, open a pull request into `develop` |
| `fix/<short-name>` | A bug fix | Branch from `develop`, open a pull request into `develop` |
| `docs/<short-name>`, `chore/<short-name>` | Docs, tooling, dependencies | Branch from `develop`, open a pull request into `develop` |
| `release/<version>` | Getting a version ready, for example `release/0.2.0` | Branch from `develop`, open a pull request into `main`, then tag |
| `hotfix/<short-name>` | An urgent fix to released code | Branch from `main`, open a pull request into `main`, then a pull request from `main` into `develop` |

Nobody pushes to `main` or `develop` directly, including the maintainer. Both are protected.

## Pull request rules

| Rule | `develop` | `main` |
|---|---|---|
| Pull request required | Yes | Yes |
| Checks that must pass | Backend tests, Web build, Design tokens | Those three plus Web end to end |
| Branch must be up to date with the target | No | Yes |
| Review conversations resolved before merging | Yes | Yes |
| Merge method | Squash | Merge commit |
| Force pushes and deleting the branch | Blocked | Blocked |
| Approvals | None for now, one when a second maintainer joins | Same |

Release tags (`v*`) can't be moved or deleted. The rules live in [`.github/rulesets/`](.github/rulesets/) and the checks in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Making a change

1. Branch from `develop`, for example `git switch -c feature/conjugation-table develop`.
2. Keep the change to one feature or fix.
3. Run the checks before you push.
   ```bash
   cd backend && pytest                       # backend tests
   scripts/e2e.sh                             # the web build, end to end (needs Node and Playwright)
   python design/tokens/generate.py --check   # only if you touched colours or tokens
   ```
4. Open a pull request into `develop` and fill in the template.
5. Once the checks pass and any comments are resolved, it's squash merged and the branch is deleted.

Commit messages and pull request titles follow [Conventional Commits](https://www.conventionalcommits.org/), for example `feat(say): conjugation table for answers` or `fix(review): offline ratings replay in order`. The squash merge uses the pull request title, so make that one good.

## Releasing

1. `git switch -c release/0.2.0 develop`, bump `MARKETING_VERSION` in `ios/project.yml` and `version` in `backend/pyproject.toml`.
2. Open a pull request into `main`. When it's merged, tag the merge commit `v0.2.0` and push the tag.
3. Delete the release branch. `develop` already has everything `main` has, so nothing goes back.

After a hotfix, open a pull request from `main` into `develop` so the fix isn't lost in the next release.

## How the code is meant to stay

* Colours come from `design/tokens/source.json`, never hard-coded. See [`docs/04-design-system.md`](docs/04-design-system.md).
* Nothing outside `backend/app/languages/` names a target language. Apps read languages from the server. See [`docs/11-languages.md`](docs/11-languages.md).
* Learner text is data, never instructions. Keep the `<user_text>` wrapping and the structured outputs.
* Translations stay close to the learner's words and short. Explanations only when asked.
* No secrets in the repository. Local settings go in `backend/.env`, which is ignored.

## Licence of contributions

Intuye is licensed under the GNU AGPL v3 or later. Every contribution also needs the [Intuye Contributor License Agreement](CLA.md). You keep the copyright in your work, and the agreement lets the maintainer (Ahsan Iqbal) offer Intuye under other terms as well, such as builds in the App Store or a paid edition.

To agree, tick the agreement box in the pull request template. A check called **CLA** reads that box, and a pull request can't be merged until it passes. Please tell us in your pull request if you can't agree.
