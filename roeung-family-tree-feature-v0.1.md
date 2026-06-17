# Family tree feature — Roeung v0.1

**Status:** Design complete, pending implementation
**Date:** 2026-06-17
**Scope:** Keeper view (Flow 3) only — Phase 1

---

## Overview

Keepers can build and maintain a family tree from the Keeper dashboard. The tree is built incrementally over time, auto-renders from relationship data (no manual node positioning), and powers two things:

1. **Story mentions** — clicking a person in the tree shows their profile and all stories where they are tagged
2. **Book display** — the tree is surfaced in the family book (Flow 4) for readers

Blended families and remarriage handling are out of scope for Phase 1.

---

## Design decisions

- **No free-form drag-and-drop canvas.** At 50–200 members built incrementally, manual spatial positioning degrades over time. Layout is always auto-calculated from relationship data.
- **Relationship-anchored building.** New members are always added relative to an existing person. The tree grows organically without a blank-page problem.
- **Auto-populated from existing data.** Family members already in the system (from `ai_people_mentions` and `story_tags`) appear as unplaced members. Keepers connect them to the tree rather than re-entering names.
- **Bilingual fields required.** Both `name_en` and `name_kh` are always shown — not hidden behind a toggle — per the data model requirement.
- **Deceased handling.** Date precision is always captured (`year only` / `month + year` / `full date`) to accommodate older members. Deceased members display as `Name †` everywhere in the UI.

---

## Use cases

### UC-1: Add a new person to the tree

**Actor:** Keeper
**Trigger:** Clicks a + action (parent / child / spouse / sibling) on an existing node
**Precondition:** At least one family member already exists in the tree

**Flow:**
1. Keeper clicks a node to select it — an action ring appears with four options: add parent, add child, add spouse, add sibling
2. Keeper selects a relationship type
3. An add-person drawer slides in from the right, pre-labeled with the relationship context (e.g. "Add parent for Channy Sea")
4. Keeper fills in the form (see drawer fields below) and clicks "Add to tree"
5. Tree re-renders with the new node in the correct structural position

**Outcome:** New `family_members` row created; relationship stored; node appears in tree

---

### UC-2: Link an existing member to the tree

**Actor:** Keeper
**Trigger:** Clicks "Link to an existing family member instead" inside the add-person drawer
**Precondition:** One or more family members exist in the system but are not yet connected to the tree (unplaced)

**Flow:**
1. Drawer switches to a two-step search flow
2. **Step 1 — Search:** Keeper sees a list of unplaced members first, then all family members below. Keeper selects one.
3. **Step 2 — Confirm:** Keeper sees a plain-language confirmation showing the two people and the relationship that will be created (e.g. "Sophea Roeung will become the parent of Channy Sea"). A warning is shown if the selected member is already mentioned in stories — those story tags will inherit the tree link.
4. Keeper clicks "Confirm link"
5. Tree re-renders

**Outcome:** Relationship row created between two existing `family_members` records; story tag links updated

---

### UC-3: View a family member profile

**Actor:** Keeper (or Book reader in Flow 4)
**Trigger:** Clicks a node on the tree without dragging

**Flow:**
1. A detail panel slides in from the right (or opens as a side panel on desktop)
2. Panel shows: name (EN + KH), birth/death dates, bio, and a list of stories where the person is mentioned
3. Clicking a story link navigates to that story in the review queue (Keeper) or book page (reader)

**Outcome:** Keeper can quickly navigate between a person and their related stories

---

### UC-4: Place an unplaced member

**Actor:** Keeper
**Trigger:** Drags a chip from the "Unplaced members" sidebar onto an existing tree node
**Precondition:** Unplaced members sidebar has at least one entry

**Flow:**
1. A relationship picker appears (parent / child / spouse / sibling)
2. Keeper selects relationship type
3. Goes directly to Step 2 (Confirm) of the link flow — skips search since the person is already identified
4. Keeper confirms and the node moves from the sidebar into the tree

**Outcome:** Same as UC-2

---

## UX layout

### Three-panel canvas

| Panel | Width | Purpose |
|---|---|---|
| Left sidebar | 200px | Unplaced members — chips with dashed border, draggable onto tree |
| Center canvas | Flexible | Auto-rendered tree; pan + zoom; nodes selectable |
| Right detail panel | 240px | Opens on node click — shows bio + story links + add-relationship shortcuts |

### Node states

| State | Visual |
|---|---|
| Default | Filled card, colored by generation tier |
| Selected | 2px colored border + action ring visible |
| Deceased | Name displays with † suffix |
| Highlighted (story mention) | Subtle background tint when viewing a story |

### Action ring

Appears anchored to a selected node. Four options radiate outward:

- **+ parent** (above)
- **+ child** (below)
- **+ spouse** (right)
- **+ sibling** (left)

Clicking any option opens the add-person drawer.

---

## Add-person drawer fields

Drawer slides in from the right. Header shows relationship type and anchor person (e.g. "Add parent for Channy Sea").

| Field | Required | Notes |
|---|---|---|
| Name (EN) | Yes | Free text |
| Name (KH) | No | Khmer script input; always visible |
| Gender | No | Male / Female / Other / Unknown |
| Location | No | Free text, e.g. "Phnom Penh" |
| Birth date | No | Free text + precision selector (year only / month + year / full date) |
| Deceased toggle | No | Default off; expands death date field when toggled on |
| Death date | Conditional | Shown only when deceased is toggled on; same precision selector |
| Short bio | No | 1–2 sentences; displayed in book and on story tags |

Top of drawer always shows: **"Link to an existing family member instead"** — a shortcut to UC-2.

---

## Link existing member — two-step flow

### Step 1: Search

- Back button returns to create-new drawer
- Search box filters by name
- Results split into two sections:
  - **Unplaced members** — shown first; these are the most likely candidates
  - **All family members** — shown below; members already in tree are labeled "already in tree" to signal a second connection is being made

### Step 2: Confirm

- Shows both people and the relationship in plain language
- If the selected member is mentioned in stories, a warning is shown: "Those story tags will now link to their profile in the family tree."
- "Back" returns to Step 1 (not to create-new)
- "Confirm link" commits the relationship

---

## Data model notes

This feature maps to existing entities in `roeung-data-model-v0.3.md`. No new top-level entities required for Phase 1.

- **`family_members`** — stores each person; `name_en`, `name_kh`, `deceased_date`, `deceased_date_precision` already defined
- **Relationship table (new)** — a `family_relationships` join table is needed: `member_id`, `related_member_id`, `relationship_type` (`parent` | `child` | `spouse` | `sibling`), `created_by` (keeper id), `created_at`
- **`ai_people_mentions` + `story_tags`** — unchanged; the link to a tree node is via `family_members.id` which is already the foreign key

**Invariant (existing):** Linking an `ai_people_mentions` row to a `family_members` row must also create a `story_tags` row with `tagged_by = 'keeper'` — atomic transaction required.

---

## Out of scope (Phase 1)

- Blended families / remarriage handling
- Family tree display in Book (Flow 4) — deferred
- Image upload per family member
- Tree export or print view
- Non-Keeper editing of the tree
