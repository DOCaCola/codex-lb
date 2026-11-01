## Why

Dashboard account cards don't share one layout. The live dashboard shows these causes:

- Every Codex card adds a footer wrapper even when the footer is empty, so its strip sits 11 px higher than a Claude strip.
- The footer and strip move depending on which of them a card has, so the credits line of a card with a warning sits higher than on a card without one.
- Grid items stretch only to the tallest card in their own row, so cards in different rows have different heights.
- Strips show only a short label ("Weekly limit", "Subscription ends 1. Nov.") without the time left.

OpenRouter money also uses the browser locale (`0,00 $`) while every other dashboard amount uses the en-US format (`$0.00`).

## What Changes

- Each card has fixed slots: header and limits at the top, then a bottom group pinned to the bottom edge with the provider footer and a status-strip slot that is always reserved.
- Every Codex card shows its credits line, also `0 + 0 credits`, with the reset-credit button on that line also when the account is limited. The strip's remedy is Re-auth or Resume; the list row, which has no credits line, keeps the reset-credit button next to the status.
- Notices carry the time they end; strips and list rows show it, e.g. `Weekly limit · back in 2d 23h`, `Subscription ends in 7h 0m`.
- Countdowns coarsen with the time left: days only from three days on (`6d`), days and hours from one day (`2d 23h`), always hours and minutes below one day (`7h 0m`), minutes below one hour.
- From two columns on, every card gets the height of the tallest card; a single column keeps natural heights.
- OpenRouter amounts use the en-US currency format, keeping sub-cent balance precision; the card's today cost uses the shared formatter.

## Capabilities

### Modified Capabilities

- `frontend-architecture`: dashboard account card layout, notice times and OpenRouter amount formatting.
