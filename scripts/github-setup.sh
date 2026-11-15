#!/usr/bin/env bash
# One-time GitHub setup for the repository owner. Needs the GitHub CLI signed in (gh auth login).
# Imports the rulesets in .github/rulesets, sets merge options and default branch, turns on security features.
set -euo pipefail
REPO="${1:-AiKoushik/intuye}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Merge options and default branch"
gh api -X PATCH "repos/$REPO" -F allow_merge_commit=true -F allow_squash_merge=true -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true -F allow_update_branch=true -f squash_merge_commit_title=PR_TITLE \
  -f squash_merge_commit_message=PR_BODY -f default_branch=develop >/dev/null

echo "Rulesets"
for file in "$ROOT"/.github/rulesets/*.json; do
  name="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$file")"
  id="$(gh api "repos/$REPO/rulesets" --jq ".[] | select(.name == \"$name\") | .id")"
  if [ -n "$id" ]; then gh api -X PUT "repos/$REPO/rulesets/$id" --input "$file" >/dev/null; echo "  updated $name"
  else gh api -X POST "repos/$REPO/rulesets" --input "$file" >/dev/null; echo "  created $name"; fi
done

echo "Security features"
gh api -X PUT "repos/$REPO/private-vulnerability-reporting" >/dev/null
gh api -X PUT "repos/$REPO/vulnerability-alerts" >/dev/null
gh api -X PUT "repos/$REPO/automated-security-fixes" >/dev/null
echo '{"security_and_analysis":{"secret_scanning":{"status":"enabled"},"secret_scanning_push_protection":{"status":"enabled"}}}' |
  gh api -X PATCH "repos/$REPO" --input - >/dev/null

echo "Done. Check Settings, Rules, Rulesets on GitHub."
