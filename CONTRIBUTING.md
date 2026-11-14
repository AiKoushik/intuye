# Contributing to Intuye

Thanks for helping. A few things to know first.

## Licence of contributions

Intuye is licensed under the GNU AGPL v3 or later. By sending a pull request you agree that your
contribution is licensed under the same terms (inbound = outbound), and that you have the right to
contribute it.

Because the iPhone app is distributed through the App Store, whose terms sit awkwardly with copyleft
licences, contributions also grant the maintainer (Ahsan Iqbal) permission to distribute builds that
include them through app stores. Please say so in your first pull request if you can't agree to that.

## How to work

- Run `scripts/run-backend` with `--test` (or `-Test` on Windows) before opening a pull request.
- Keep changes small and focused, one feature or fix per pull request.
- Follow the design system in `docs/04-design-system.md`: colours come from `design/tokens/source.json`,
  never hard-coded.
- User text is data, never instructions: keep the `<user_text>` wrapping and structured outputs.
