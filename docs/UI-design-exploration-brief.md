# Eva UI — design exploration brief

A lean brief for **exploring** visual directions for Eva's interface (e.g. in Claude
Design). This is *not* a locked spec — it gives just enough identity, palette, and screen
context to generate on-brand directions, then explore freely. Build target is **Flutter**
(web first, native mobile later), so treat any generated React/HTML as a **visual
reference**, not final code.

> Canonical color theme is **official Catppuccin Macchiato** (below). **Ignore** the
> neon-green/blue theme in `docs/technical-architecture.html` — that's an old demo, not the
> direction.

---

## What Eva is

A **character-first AI companion** — not a tool with a personality bolted on. You talk to
Eva in natural conversation; she remembers what matters to you, keeps your story, and takes
initiative. The conversation *is* the product (text-first). The UI should feel like **her
space** — personal, warm, a little moody — the opposite of a sterile assistant chat.

## Who Eva is (for avatar / mood / vibe)

Half-fox, half-human: white fox ears, a fluffy white tail, silky **silver** hair, sharp
**violet** eyes. Casual, loosely-fitted clothes in soft muted colors. Personality: grumpy,
sassy, dry — but genuinely caring underneath (~70% prickly, 30% soft slipping through). The
sass is affection wearing armor. (Full persona: `persona/eva.md`.)

**Vibe words:** cozy, personal, dim/dusky, soft edges, a touch moody, unhurried. Think
"her room at dusk," not "enterprise dashboard." Dark theme throughout.

## Canonical palette — Catppuccin Macchiato (official)

Base / surfaces (dark):
- Crust `#181926` · Mantle `#1e2030` · **Base `#24273a`** (app background)
- Surface0 `#363a4f` · Surface1 `#494d64` · Surface2 `#5b6078`
- Overlay0 `#6e738d` · Overlay1 `#8087a2` · Overlay2 `#939ab7`

Text:
- **Text `#cad3f5`** · Subtext1 `#b8c0e0` · Subtext0 `#a5adcb`

Accents:
- Rosewater `#f4dbd6` · Flamingo `#f0c6c6` · **Pink `#f5bde6`** · **Mauve `#c6a0f6`**
- Red `#ed8796` · Maroon `#ee99a0` · Peach `#f5a97f` · Yellow `#eed49f`
- **Green `#a6da95`** · Teal `#8bd5ca` · Sky `#91d7e3` · Sapphire `#7dc4e4`
- Blue `#8aadf4` · **Lavender `#b7bdf8`**

**Suggested primary accent: Mauve `#c6a0f6`** (echoes Eva's violet eyes), with Pink/Lavender
as secondary — but exploring other accents is welcome. One accent should lead; Catppuccin
looks best with a single dominant accent + restrained use of the rest (e.g. Green for
"saved/remembered" confirmations, Red/Maroon for destructive).

## Typography

No decision yet — explore. Leaning: a warm **humanist sans** for UI (e.g. Inter, Lexend, or
something a touch rounder/cozier like Quicksand/Nunito for headers). Optional idea worth
trying: give **Eva's messages** a subtly distinct treatment from yours/system text so her
voice reads as *hers*.

## Screens / surfaces to explore (v1)

Lead with the first two; the rest are lower priority.
1. **The conversation** — the heart. Eva's messages vs. your messages, how her snark/warmth
   reads visually, timestamps kept quiet, an input that feels inviting. This is 80% of it.
2. **Eva's presence** — how is she *here*? An avatar, a mood/expression cue, a small
   ambient sense of her in the room. Explore subtle → expressive.
3. **"What Eva remembers about you"** — a gentle view of what she's saved (her notebook /
   the memory she keeps). Character-first, never "database of facts."
4. **Settings** — quiet and minimal. Includes a **daily-driver model switcher** (a small
   curated dropdown: which "brain" Eva runs on).

## Hard constraints (keep these true across every direction)

- **Dark theme**, Catppuccin Macchiato.
- **Mobile-responsive** — it becomes a native mobile app later; design so the chat works
  one-handed on a phone, not just on a wide desktop.
- **Text-first** — the conversation is primary; chrome stays out of the way.
- **Character-first language** — no tool-speak. Not "Entry saved" → more like
  "*jots it down*". Eva participates in a relationship, she doesn't serve a user.

---

## Starter prompt (paste into Claude Design)

> Design a **dark, cozy chat interface** for **Eva**, a character-first AI companion (not a
> productivity tool). Eva is a sassy-but-caring fox-girl character — white fox ears, silver
> hair, **violet** eyes — and the UI should feel like *her* personal space: warm, dim, soft
> edges, a little moody; "her room at dusk," not an enterprise app. Use the **Catppuccin
> Macchiato** palette: background Base `#24273a`, text `#cad3f5`, primary accent **Mauve
> `#c6a0f6`** (her eye color), with Pink `#f5bde6` / Lavender `#b7bdf8` as secondary and
> Green `#a6da95` for "remembered/saved" moments. Start with the **main conversation
> screen**: distinguish Eva's messages from mine so her voice feels like hers, an inviting
> message input, quiet timestamps. Then explore **how Eva is present** (an avatar / mood
> cue). It must be **mobile-responsive** (becomes a phone app later) and **text-first**.
> Give me **a few distinct directions** to compare — vary how expressive Eva's presence is
> and how playful vs. minimal the styling feels.
