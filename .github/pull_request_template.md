<!-- Feature work targets develop. Only release/* and hotfix/* branches target main. -->

## What this changes

<!-- One or two sentences. Link the issue it closes, e.g. "Closes #12". -->

## How I checked it

- [ ] `pytest` passes in `backend/`
- [ ] `scripts/e2e.sh` passes (for changes to the web build or the API)
- [ ] `python design/tokens/generate.py --check` passes (for colour or token changes)
- [ ] iPhone code builds in Xcode (for changes under `ios/`), or I said below that I couldn't build it

## Checklist

- [ ] No secrets, keys or personal data in the diff
- [ ] Nothing names a target language outside `backend/app/languages/` (see `docs/11-languages.md`)
- [ ] Docs and `docs/02-feature-list.md` updated if behaviour changed
- [ ] New text in the apps is short, specific and has no em dashes

## Contributor agreement

- [ ] I have read [CLA.md](../blob/develop/CLA.md) and I agree to it for this contribution
