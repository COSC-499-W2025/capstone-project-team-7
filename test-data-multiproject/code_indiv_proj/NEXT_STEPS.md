# Wordoku Gift App - Next Steps Checklist

## Engine
- Add more difficulty tuning (symmetry, clue distribution per 3x3 box)
- Add hints (candidate calculation, singletons, hidden singles)
- Add persistence for seeded generation per level
- Expand forced word placement (random row/col, multiple reveal options)

## Tests
- Add generator performance tests with timeouts
- Add solver regression cases (hard/evil grids)
- Add forced-column reveal test

## UI/UX
- Add level progression (multi-level list + lock/unlock)
- Add input UX (keyboard support, long-press delete)
- Add mistake counter + optional penalty
- Add animated win reveal highlighting the forced word

## Data
- Validate and filter wordlist at load (log rejects)
- Add per-difficulty word selection (length, letter patterns)

## App Structure
- Add persistence (UserDefaults) for last level and in-progress grid
- Add settings screen (conflicts toggle, difficulty default)
