# Brainiac Operations Log

This log records Brainiac write operations and important maintenance actions.

## 2026-05-11

- Initialized Brainiac project skeleton.
- Added Codex/agent entrypoint, context brief, operator context, and external source takeaways.
- Moved Brainiac repository out of the Obsidian vault into a standalone project directory.
- Implemented Phase 1 read-only inventory CLI, SQLite index writer, Markdown fact extraction, and generated inventory report.
- Ran inventory scan against the external Obsidian vault and generated the Phase 1 inventory report.

## 2026-05-20

- Added a short headphone-alternatives shortlist to `Areas/Покупки/Дорогие покупки.md` in the external vault for later review.
- Reorganized the external food vault content from `Areas/Еда/` into `Resources/Еда/`, added a Tbilisi cafe card for Rum Roof, and added a `Resources/Еда/` routing destination.
- Reorganized the external food vault further by moving `Yoko` into `Resources/Еда/Кафе/Тбилиси/`, `Carnaroli` into `Resources/Еда/Ингредиенты/`, and `The Meat Market` into `Resources/Еда/Гриль/Магазины мяса/`.
- Added additional Tbilisi cafe cards with Google Maps links: `Кета и коте`, `Кхеди`, `Сосиски с пивом`, `Вангоги`, `Бернард суши`, `Дади`, `Хоноре`, `Сантино`, and `Сэинт бани`.
- Simplified the Tbilisi cafe cards to reduce template overlap and keep maintenance noise low.
- Added `best_for` and `top_items` fields to the Tbilisi cafe notes and reshaped the umbrella to support intent-based lookup like wine, sushi, breakfast, view, tacos, and comfort food.
- Removed an accidental nested `Resources/Еда/Кафе/Тбилиси/Тбилиси.md` umbrella copy and kept `Resources/Еда/Кафе/Тбилиси.md` as the single city index.

- Added `Entree` as a Tbilisi cafe source note and indexed it under breakfast/coffee/pastries.
- Added `Coffeeshop Company Garden` as a Tbilisi cafe source note and added it to the city index.
- Updated `Coffeeshop Company Garden` to include good breakfasts in both the source note and city index.
- Created the `Resources/Путешествия/Грузия/` travel catalog, converted `Inbox/новые места грузии.md` into a reusable intake template, and moved the existing Mtskheta and DMANISI museum notes into the catalog.
- Updated `Inbox/новые места грузии.md` to use a wikilink to the `Грузия` umbrella and added `Inbox/новые кафе тбилиси.md` as a separate intake file for future cafe captures.
- Added `Grilla` as a Tbilisi cafe source note for burger/meat intent and indexed it in the city note.
- Renamed the Georgia places/museums inbox note to `Inbox/новые места грузии.md` and marked it as `brainiac_role: source`.
- Standardized `Inbox/новые места грузии.md` into a reusable entry template for quick place reviews.
- Fixed the cafe inbox wikilink to point at `[[Тбилиси]]`, matching the note basename so maintenance resolves it cleanly.

## 2026-07-23

- Removed the obsolete reference to the retired derived note from `Areas/Здоровье/Анализы/summary.md`; the health-analysis umbrella now points only to its source notes.
- Added explicit `brainiac_role: source` markers to four non-sensitive vault notes, configured `Areas/Gamedev/` as an area destination, and removed the empty `Untitled/` and `Винодельни/` directories.
- Added the confirmed `brainiac_role: source` marker to `Areas/Семья/Дети.md` without changing its content.
