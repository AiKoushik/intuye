# One-time GitHub setup for the repository owner. Needs the GitHub CLI signed in (gh auth login).
# Imports the rulesets in .github/rulesets, sets merge options and default branch, turns on security features.
$ErrorActionPreference = "Stop"
$Repo = if ($args.Count -gt 0) { $args[0] } else { "AiKoushik/intuye" }
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "Merge options and default branch"
gh api -X PATCH "repos/$Repo" -F allow_merge_commit=true -F allow_squash_merge=true -F allow_rebase_merge=false `
  -F delete_branch_on_merge=true -F allow_update_branch=true -f squash_merge_commit_title=PR_TITLE `
  -f squash_merge_commit_message=PR_BODY -f default_branch=develop | Out-Null

Write-Host "Rulesets"
$existing = gh api "repos/$Repo/rulesets" | ConvertFrom-Json
foreach ($file in Get-ChildItem (Join-Path $Root ".github/rulesets/*.json")) {
  $name = (Get-Content $file.FullName -Raw | ConvertFrom-Json).name
  $old = $existing | Where-Object { $_.name -eq $name }
  if ($old) { gh api -X PUT "repos/$Repo/rulesets/$($old.id)" --input $file.FullName | Out-Null; Write-Host "  updated $name" }
  else { gh api -X POST "repos/$Repo/rulesets" --input $file.FullName | Out-Null; Write-Host "  created $name" }
}

Write-Host "Security features"
gh api -X PUT "repos/$Repo/private-vulnerability-reporting" | Out-Null
gh api -X PUT "repos/$Repo/vulnerability-alerts" | Out-Null
gh api -X PUT "repos/$Repo/automated-security-fixes" | Out-Null
'{"security_and_analysis":{"secret_scanning":{"status":"enabled"},"secret_scanning_push_protection":{"status":"enabled"}}}' |
  gh api -X PATCH "repos/$Repo" --input - | Out-Null

Write-Host "Done. Check Settings, Rules, Rulesets on GitHub."
