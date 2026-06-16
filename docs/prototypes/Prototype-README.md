
# Roeung — Design Reference

A private family oral-history web app. Family members record or upload spoken stories; "Keepers" curate them; everyone reads and listens to the resulting bilingual family book.

> **These files are design references, not production code.** Recreate the designs in your target stack (React, etc.) using its own patterns and libraries. Do not ship the HTML directly.

## Files in this folder

Each surface exists in two forms:

| File | What it is | Use it to… |
|------|-----------|------------|
| `Roeung *.html` | Self-contained, **runnable** bundles | **Open in a browser** to see live behavior, animation, and the EN/KH toggle |
| `Roeung *.dc.html` | Readable **source** (markup + logic class + all copy) | Read for component structure, audio/waveform logic, and exact bilingual strings |

- **Capture** — record/upload flow for any family member
- **Book** — the family archive: read & listen
- **Keeper** — curator workspace: review & publish
- **Direction** — the visual identity / source of truth for tokens
- **Index** — landing page linking the prototypes (not a product surface)

## Fidelity

**High-fidelity.** Colors, type, spacing, and interactions are intended to be matched closely. Build a token layer first, then the screens.

---

## Design tokens

### Type
- **Newsreader** (serif) — titles, headings, story text, narrator names
- **Hanken Grotesk** (sans) — body, labels, UI, metadata, buttons
- **Noto Serif Khmer** (serif) — all Khmer text
- Uppercase labels: Hanken 600, ~10–11px, `letter-spacing: 0.14–0.22em`
- Slide/screen titles: Newsreader 500, `letter-spacing: -0.01em`

### Color
| Role | Hex |
|------|-----|
| Ink (primary text, dark buttons, phone bezel) | `#2a2620` |
| Body / muted text | `#6f685b` |
| Faint text / meta | `#8c8576`, `#a99f8c` |
| Off-white surfaces (cards) | `#faf8f3`, `#f3f1ea`, `#ffffff` |
| Sand (page bg, chips, toggles) | `#e9e3d6`, `#d9d4c9`, `#efeae0` |
| **Clay accent** (primary accent, dagger, active waveform) | `#a3623e` |
| Clay tint (icon wells, selected chip) | `#f4e7da` |
| Warn (translation flag, noise) — text on bg | `#9a6a32` on `#f6ecdc`, border `#e3cba6` |
| Danger (discard / delete) | `#bf4528` |
| Confirm / success | `#5f7d52` |

### Shape & elevation
- Card radius: 13–16px; phone screen radius: 42px (bezel 48–50px); pill/chip radius: 18–22px
- Soft, low shadows: e.g. `0 14px 40px -24px rgba(42,38,32,0.45)` for cards; deeper for floating panels/devices
- Hairline borders: `1px solid rgba(42,38,32,0.08)`

---

## Shared components (build these first)

1. **EN / ខ្មែរ language toggle** — small sand-colored segmented pill, present on every screen. Switches all on-screen copy. EN label is Hanken; KH label is Noto Serif Khmer. The Book story view additionally has its own EN/KH transcript sub-toggle, independent of the global one.
2. **Audio waveform** — a row of vertical bars. Bars left of the playback position render in clay `#a3623e`; bars to the right render muted `#cdbfab`. Used at multiple sizes: full player, mini confirm strip, story cards. Parameterize bar count, width, gap, max height, and progress fraction.

## Recurring conventions (apply everywhere)

- **Deceased people** are shown as `Name†` — a clay-colored dagger, superscript, ~0.82–0.92em, raised. Appears anywhere a person is named (tags, people lists, chips).
- **Approximate translations** carry a badge: `⚠ Translation approximate` — Hanken 600 ~9px, `#9a6a32` on `#f4e7d4`, `1px solid #e3cba6`, radius 5px. On flagged stories, a fuller inline warning appears above the transcript.
- **Consent is explicit and logged** — the narrator's name plus the capturer's confirmation are recorded with a timestamp before any recording begins.

---

## Surfaces

### Capture — `Roeung Capture`
Mobile-first linear flow, opened from a private link. Also has a desktop layout.

**Flow:** Home → Consent → (Record **or** Upload) → Quick Tag → Confirm & Send → Sent
- **Home:** two big choices (Record a story / Upload audio) + "Recently added" list with waveforms.
- **Consent:** gate screen; the narrator agreed to be recorded and shared. Logs name + timestamp. Cancellable.
- **Record:** large timer, pulsing record dot, live animated waveform, 60-min cap, background-noise warning, stop button. *(Prototype simulates this; real build uses `MediaRecorder`.)*
- **Upload:** drop zone + file row + progress bar. Accepts mp3, m4a, wav (max 500MB).
- **Quick Tag:** chips for family members (with `†` deceased treatment); a pre-selected narrator; "someone else" option.
- **Confirm:** mini waveform player + summary rows (duration, captured by, people tagged, consent logged). Send to Keepers, or a destructive "delete recording" with a confirm overlay.
- **Sent:** confirmation + estimated review time + record-another.

### Book — `Roeung Book`
Read & listen. Desktop + mobile.

- **Home:** family masthead, "Recently added" cards, **Chapter** shelves (e.g. *Life Before the War*, *The Khmer Rouge Period*, *Migration & Resettlement*, plus a muted *Uncategorised*).
- **Chapter:** story list with sort + narrator/language filters.
- **Story:** bilingual transcript with EN/KH sub-toggle; **people-in-this-story** tags; audio player.
- **Listen Mode (key feature):** during playback the current sentence highlights (warm underline/background); tapping any sentence seeks to it. Playback speed 0.75/1/1.25×; prev/next story nav. *(Prototype fakes timing with intervals; real build needs per-sentence audio timestamps.)*

### Keeper — `Roeung Keeper`
Curator workspace, desktop-first.

- **Sidebar:** Queue / Book / Members / Chapters / Flagged, with count badges; keeper identity at the bottom.
- **Queue:** incoming stories with sort + filter chips; per-row flags — translation-approximate, **🔒 locked** (another keeper is reviewing), language, duration.
- **Review:** audio player with an **editable** bilingual transcript, a title picker, people tagging, and a decision bar (publish / request changes). 
- **Published:** confirmation state.

---

## Data model (suggested)

Stories (audio + per-sentence transcript with timestamps, EN + KH), narrators, chapters, people (with `deceased` flag), consent records (narrator, confirmer, timestamp), translation-approximate flag, review/lock state, keepers. The prototypes use mock data — replace with your API.
