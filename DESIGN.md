---
name: agent-skills
description: A workshop shadow board for a personal agent-skill library — painted tool shadows on perforated hardboard, a red steel rail, one engraved plate under the lamp.
colors:
  board: "#ebe7dc"
  hole: "#8a8577"
  hole-rim: "#d8d3c5"
  shadow: "#151412"
  ink: "#1c1a17"
  ink-2: "#4a463f"
  red: "#c0111f"
  red-hi: "#e23545"
  red-lo: "#7d0a13"
  grip: "#c0111f"
  steel: "#787f87"
  lamp: "#ffd166"
  paper: "#f7f4ea"
  chest: "#1b1918"
typography:
  display:
    fontFamily: "Big Shoulders Display, system-ui, sans-serif"
    fontSize: "clamp(3rem, 5.2vw, 4.6rem)"
    fontWeight: 900
    lineHeight: 0.9
    letterSpacing: "0.005em"
  headline:
    fontFamily: "Big Shoulders Display, system-ui, sans-serif"
    fontSize: "clamp(2.2rem, 4.5vw, 4rem)"
    fontWeight: 800
    lineHeight: 0.92
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Big Shoulders Display, system-ui, sans-serif"
    fontSize: "1.45rem"
    fontWeight: 800
    lineHeight: 0.92
    letterSpacing: "0.02em"
  body:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Martian Mono, ui-monospace, Menlo, monospace"
    fontSize: "0.66rem"
    fontWeight: 400
    lineHeight: 1.25
    letterSpacing: "0.06em"
  command:
    fontFamily: "Martian Mono, ui-monospace, Menlo, monospace"
    fontSize: "0.8rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-0.01em"
  numeral:
    fontFamily: "Big Shoulders Display, system-ui, sans-serif"
    fontSize: "1.2rem"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "0.04em"
    fontVariation: "tabular-nums"
rounded:
  none: "0"
  chamfer: "2px"
  plate: "3px"
  panel: "4px"
  pull: "20px"
  dot: "50%"
spacing:
  half: "12px"
  cell: "24px"
  cell-and-half: "36px"
  two-cell: "48px"
  three-cell: "72px"
components:
  rail:
    backgroundColor: "{colors.red}"
    textColor: "#ffffff"
    padding: "14px 24px"
  install-plate:
    backgroundColor: "#c9ccc9"
    textColor: "#1f2225"
    typography: "{typography.command}"
    rounded: "{rounded.plate}"
    padding: "10px 14px 10px 18px"
  copy-button:
    backgroundColor: "#151719"
    textColor: "#ffffff"
    typography: "{typography.label}"
    rounded: "{rounded.chamfer}"
    padding: "7px 12px"
  copy-button-hover:
    backgroundColor: "#1d2022"
  copy-button-done:
    backgroundColor: "{colors.lamp}"
    textColor: "#1a1c1e"
  hang-switch:
    backgroundColor: "#5a0d15"
    rounded: "13px"
    width: "54px"
    height: "26px"
  hang-switch-on:
    backgroundColor: "{colors.lamp}"
  tool-cell:
    backgroundColor: "transparent"
    textColor: "{colors.shadow}"
    typography: "{typography.label}"
    rounded: "{rounded.panel}"
    width: "168px"
    height: "240px"
  tool-cell-hung:
    textColor: "{colors.steel}"
  inventory-tag:
    backgroundColor: "#e6ddc2"
    textColor: "{colors.ink}"
    rounded: "3px 14px 3px 3px"
    padding: "16px 18px 14px 22px"
    width: "420px"
  paper-note:
    backgroundColor: "#ece7d6"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "16px 20px 14px"
  inventory-sheet:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "36px 24px 24px"
  drawer:
    backgroundColor: "{colors.red}"
    textColor: "#ffffff"
    rounded: "{rounded.panel}"
    padding: "18px 24px"
  drawer-pull:
    backgroundColor: "#b8bec4"
    textColor: "#1a1c1e"
    typography: "{typography.command}"
    rounded: "{rounded.pull}"
    padding: "10px 14px"
---

# Design System: agent-skills

## Overview

**Creative North Star: "The Shop Shadow Board"**

This is a wall in a workshop, photographed under one lamp. The ground is perforated off-white hardboard with its hole lattice fully drawn, not suggested: every 24px there is a drilled hole with a rim and a highlight, and that lattice runs edge to edge behind everything. Bolted across the top is a red steel tool-chest rail with the name embossed into it. Screwed to the rail is a single brushed aluminium plate carrying the install command, engraved, and it is the only thing on the page that emits light. Everything else on the board is painted black: 23 tool silhouettes hanging from steel hooks, each stencilled with its skill name and its use count. Flip the switch on the rail and the paint becomes metal — the same 23 shapes fill in as grey steel with red grips and drop onto their hooks one after another.

The density is high and deliberately unmodern. There is no card grid, no rounded panel with a soft shadow, no gradient hero. Depth here is physical and specific: hardboard is grainy and matte, steel is a hard gradient with a one-pixel highlight and a two-pixel dark lip, paper is square-cut with a piece of tape or two push pins holding it, and aluminium under a lamp throws an amber halo. Type follows the same logic — headings are painted signage in a compressed display face, every label is stamped mono capitals, and body copy only ever appears on paper.

The world has one accent and one light. Red is structural, not decorative: it is the rail, the drawers, the tool grips, the focus ring, the text selection, the scrollbar. Amber appears only where something is lit or thrown. Nothing is greyed out to look "secondary" — the quiet state of this page is black paint on off-white board, and that state is the default.

**Key Characteristics:**
- A 24px pegboard hole lattice as the literal layout grid, visible behind every section
- Painted-black tool silhouettes as the resting state; steel-and-red tools as the acted-upon state
- One lit element (the engraved install plate) and one lamp colour used only for lit states
- Materials rendered with real gradients, inset bevels and grain, not flat colour fills
- Two type poles: painted display capitals and stamped mono labels, with almost nothing between
- Paper (notes, tag, inventory sheet) is the only surface body copy is allowed to sit on

## Colors

Workshop stock: aged hardboard, safety red, shop-lamp amber, and one grey steel — a palette taken from the objects, not from a ramp generator.

### Primary
- **Safety Red** (`#c0111f`): the steel of the rail and the drawer fronts, the tool grips when tools are hung, the focus ring on light ground, the selection highlight, the scrollbar thumb, and the link colour on paper. It is the structure of the page, so it carries a highlight and a shade for modelling metal rather than for state.
- **Rail Highlight** (`#e23545`) and **Rail Shade** (`#7d0a13`): the top and bottom stops of the rail gradient only. They exist to make a cylinder of steel; they are never used as flat fills.
- **Grip Red** (`#c0111f`): the same value as Safety Red, aliased for the painted grip of a hung tool so the tool's own colour logic stays readable in the SVG symbols.

### Secondary
- **Shop-Lamp Amber** (`#ffd166`): the one light in the room. It is the plate's halo, the thrown position of the hang switch, the "Copied" state of a copy button, the focus ring on red and dark ground, and a single accented phrase in the tool-chest heading. It is never a background for body copy and never a decorative tint.

### Tertiary
- **Tool Steel** (`#787f87`): the body of a hung tool. It exists only in the hung state and only inside the tool silhouettes; the chrome of the hooks, screws and drawer pulls is drawn with literal near-white to near-grey gradients rather than from this token.

### Neutral
- **Hardboard** (`#ebe7dc`): the board field, the page background, and the knock-out plate behind any label that sits on the lattice.
- **Drilled Hole** (`#8a8577`) and **Hole Rim** (`#d8d3c5`): the two-stop radial that makes each perforation read as a hole with a chamfered lip. Only ever used inside the board's background image.
- **Shadow Paint** (`#151412`): the black of the painted tool silhouettes and of the big painted headings. This is the darkest value on the board and it reads as paint, not as text colour.
- **Ink** (`#1c1a17`): body and label text on board and paper.
- **Ink Soft** (`#4a463f`): lede copy, step descriptions, table meta columns, and the caption under a numeral. The only "muted" value in the system.
- **Shop Paper** (`#f7f4ea`): the inventory sheet and the drawer name labels. Notes and the inventory tag use their own slightly warmer two-stop paper gradients.
- **Chest Dark** (`#1b1918`): the terminus of both dark grounds — the tool-chest section and the bench footer — and the scrollbar track.

### Named Rules
**The One Lamp Rule.** Amber is light, not decoration. It may appear only where something is genuinely lit or switched: the engraved plate's halo, a thrown switch, a completed copy, and focus on dark ground. If a second element glows, the first one stops meaning anything.

**The Red Is Structure Rule.** Red is the steel of the page — rail, drawers, grips, focus, selection. It is never used as a background for a paragraph and never as an emphasis tint on paper. When red appears on paper it appears as a 1.5px underline or a link, at text weight.

**The No Grey-Out Rule.** Inactive is not dimmed. The resting state of a tool is fully saturated black paint at full opacity; the acted-upon state is steel and red. Depth of state is carried by material change, never by lowering opacity on text.

## Typography

**Display Font:** Big Shoulders Display (self-hosted variable, 100–900; falls back to `system-ui`)
**Body Font:** Archivo (self-hosted variable, 100–900; falls back to `system-ui`)
**Label/Mono Font:** Martian Mono (self-hosted variable, 100–800; falls back to `ui-monospace`, Menlo)

**Character:** A compressed American signage face doing all the shouting, a neutral grotesque doing all the reading, and a wide mono doing all the stamping. Big Shoulders is set almost exclusively in uppercase at weight 800–900 with a sub-1 line height so headings stack like painted stencil rows; Archivo never goes above 1rem; Martian Mono is never set as running text, only as capitals with open tracking.

### Hierarchy
- **Display** (900, `clamp(3rem, 5.2vw, 4.6rem)`, line-height 0.9, uppercase): the one painted headline on the board. Set in Shadow Paint with a single phrase in Safety Red. Drops to `clamp(2.6rem, 13vw, 4rem)` below 760px.
- **Headline** (800–900, `clamp(1.9rem, 3.6vw, 2.8rem)` to `clamp(2.4rem, 5vw, 4rem)`, uppercase): section titles. Painted black on board, white on the dark chest, ink on paper. Each section picks one clamp and holds it.
- **Title** (800, 1.45–1.5rem, uppercase, tracking 0.01–0.02em): step headings and the inventory tag's skill name.
- **Body** (400, 17px / 1.5; 16px below 760px): only on paper surfaces. Measures are capped explicitly — 52ch for the lede, 56ch for step copy, 60ch for drawer copy, 64ch for the footer. Emphasis is weight 600 in full Ink, never colour.
- **Label** (400–600, 0.58–0.72rem, tracking 0.03–0.08em, uppercase, mono): tool names, table headers, switch states, harness list, copy buttons, timestamp notes. Every label in the system is mono capitals.
- **Command** (600, 0.74–0.8rem, mono): install lines and shell snippets. Engraved on metal (white 1px text-shadow, dark ink) or reversed out on Shadow Paint. Never wrapped mid-word above 1100px; below it, `word-break` is allowed so the plate can hold the full line.
- **Numeral** (700–900, 0.9–1.35rem, display face, tabular): use counts under each tool, in the tag, and in the inventory sheet's right column. Numbers are set in the display face so they read as painted stock numbers, with a mono caption beside them.

### Named Rules
**The Two Poles Rule.** Type is either painted (display, 800–900, uppercase, huge) or stamped (mono, uppercase, tiny, tracked). The middle register exists only for body copy on paper, and body copy never exceeds 1rem. If a new size lands between 1.5rem and 2.2rem, it is probably a heading that should be painted or a label that should be stamped.

**The Knock-Out Rule.** Any text that sits directly on the hole lattice carries a Hardboard-coloured plate behind it (`background: #ebe7dc; padding: 0 3px`, with `box-decoration-break: clone` so wrapped lines each get their own plate). Text is never set straight onto the perforations.

## Layout

The page is built on one module: a 24px cell (`--cell`). It is simultaneously the pegboard's hole pitch, the page gutter, the section padding, and the multiplier for every larger measure — half a cell (12px) for tight rows, one and a half (36px) for paper insets, two (48px) for section rhythm, three (72px) for the page's bottom air. The board's `background-size` is exactly one cell, so the visible hole lattice and the spacing scale are the same grid.

Containers are capped at 1440px and centred, with one cell of horizontal padding. Sections alternate between board-ground (hero, shop rules, inventory sheet) and material interruptions (the red rail, the dark tool chest, the dark bench footer), so the lattice reappears rather than running unbroken down the page.

Content grids are asymmetric twelfths, never halves: the hero head is 7fr / 5fr with the two columns aligned to their baselines (`align-items: end`), and the shop-rules grid is 5fr / 7fr with a two-cell gap. The tool board is a zero-gap `auto-fill` grid of 7-cell-wide (168px) by 10-cell-tall (240px) cells, left-justified — the gap is zero on purpose so the perforations, not whitespace, are the gutters between tools.

Three breakpoints, each doing one job:
- **1300px** — the board tightens: tool cells drop to 9 cells tall and silhouettes to 80×140.
- **1100px** — the rail restacks to two columns, the harness list is dropped, and the install plate moves to the left and is allowed to wrap onto multiple lines.
- **760px** — base type drops to 16px, the rail stops being sticky, every two-column grid collapses to one, the tool board becomes a fixed centred 3-column grid of 5-cell-wide cells with 72×126 silhouettes and 0.58rem names, the inventory tag leaves its sticky layer and becomes an in-flow card under the board, the inventory table drops its header row and re-forms each row as a two-column card, and the inventory sheet loses its rotation.

### Named Rules
**The Board Is The Grid Rule.** Every measurement is a whole or half multiple of the 24px cell, because the cell is visible. A value that does not land on the lattice will be seen as off, so there are no arbitrary paddings in the layout scale.

**The Zero-Gutter Board Rule.** Tool cells touch. Do not introduce grid gap on the board; separation comes from the silhouettes' own internal margin and from the lattice showing through.

## Elevation & Depth

This system is emphatically not flat, and it does not use a generic elevation ramp. Depth is material simulation: every raised surface is a linear gradient plus a 1px white inset at the top edge and a dark inset at the bottom edge (the lip), then a cast shadow below it. Every recessed surface inverts that. The whole page is lit from the upper left by a single overlay on the board (`linear-gradient(160deg, rgba(255,255,255,.35), transparent 40%, rgba(40,35,25,.10))`) plus a multiply-blended fractal-noise grain at 0.35 opacity, and every cast shadow in the system is offset down and to the right to agree with it.

Painted shadows and real shadows are deliberately different. A silhouette at rest carries a tight `drop-shadow(1px 2px 1.5px rgba(21,20,18,.35))` — paint lying almost flat on the board. A hung tool carries `drop-shadow(2px 5px 4px rgba(21,20,18,.45))` — an object standing off the board. That single change is the depth story of the page.

### Shadow Vocabulary
- **Rail steel** (`0 10px 24px -6px rgba(20,10,10,.55), inset 0 1px 0 rgba(255,255,255,.35), inset 0 -2px 0 rgba(0,0,0,.35)`): the bolted-on header. Deep, tight-spread cast shadow so the rail sits proud of the board.
- **Lit plate** (`inset 0 1px 0 rgba(255,255,255,.7), inset 0 -1px 0 rgba(0,0,0,.25), 0 4px 10px -2px rgba(0,0,0,.45), 0 0 0 1px rgba(0,0,0,.25), 0 8px 34px 2px rgba(255,209,102,.55)`): the only amber bloom in the system. Reserved for the single lit element.
- **Painted shadow** (`drop-shadow(1px 2px 1.5px rgba(21,20,18,.35))`): resting tool silhouettes and hooks.
- **Hung tool** (`drop-shadow(2px 5px 4px rgba(21,20,18,.45))`): tools in their hung state.
- **Paper on board** (`0 8px 18px -8px rgba(21,20,18,.5), 0 0 0 1px rgba(21,20,18,.16)`) and **sheet on board** (`0 10px 30px -8px rgba(21,20,18,.5), 0 0 0 1px rgba(21,20,18,.18)`): notes and the inventory sheet. The hairline ring is the paper's cut edge, not a border.
- **Hanging tag** (`0 6px 18px -4px rgba(21,20,18,.5), 0 0 0 1px rgba(21,20,18,.25)`): the inventory tag floating over the board.
- **Drawer front** (`inset 0 1px 0 rgba(255,255,255,.35), inset 0 -3px 0 rgba(0,0,0,.4), 0 6px 14px -4px rgba(0,0,0,.7)`): painted steel drawer in the dark chest — a 3px bottom lip, the heaviest inset in the system.
- **Pressed control** (`inset 0 2px 4px rgba(0,0,0,.7), 0 1px 0 rgba(255,255,255,.25)`): the switch track, recessed into the rail. The only inverted element.

### Named Rules
**The One Lamp Rule (depth form).** The light comes from the upper left, once. Every cast shadow is offset positively in x and y; no element casts upward, and no element gets its own light source.

**The Two Shadows Rule.** Paint casts a 2px shadow; an object casts a 5px shadow. When something transitions from represented to real, change the shadow — that is how state is shown here, not with opacity or an outline.

## Shapes

Corners are nearly square, and the radius tells you what the thing is made of. Paper has no radius at all: the note cards, the shop-rules sheet and the inventory sheet are square-cut rectangles, held by a translucent tape strip (a `-2deg` multiply-blended bar over the top edge) or by two radial-gradient push pins. Metal gets a chamfer: 2px on stamped controls and code chips, 3px on the engraved plate and the drawer pull's code window, 4px on drawer fronts and tool cells. Only hardware that is meant to be gripped goes fully round — the drawer pull is a 20px pill, the switch a 13px track, and screws, pins, eyelets and the switch knob are perfect circles.

The signature silhouette is the inventory tag: a 3px base radius with a 14px top-right radius, then an actual `clip-path` polygon cutting a 22px corner off — a punched card tag, with a circular eyelet inset at the top left. It is the only clipped shape in the system and it is not reused elsewhere.

All 23 tool silhouettes are drawn on one shared `viewBox` of `0 0 120 220` and rendered at one shared size, so a spirit level and a padlock hang at the same scale on the same baseline. Holes in a tool are punched through to the board colour rather than filled with a lighter grey, which is what makes the painted state read as a stencil.

### Named Rules
**The Material Radius Rule.** Paper is square (0), metal is chamfered (2–4px), grips are round (pill or circle). Do not round a paper surface, and do not square off a pull.

**The One Scale Rule.** Every tool is drawn in the same 120×220 frame and displayed at the same size, hanging from the same hook at the same height. A tool never gets bigger because it matters more; its use count says that instead.

## Components

### Buttons
- **Shape:** stamped chamfer (2px), no border.
- **Copy (primary):** dark steel gradient (`#2b2e31` → `#151719`), white mono capitals at 0.72rem with 0.06em tracking, 7px 12px padding, a 1px white inset highlight over a 2px cast shadow. This is the only button style in the system; it appears on the plate, on each drawer pull, and beside each shop-rule command, shrinking to 0.64rem inside drawer pulls.
- **Hover / Active:** the gradient lightens (`#3a3e42` → `#1d2022`) over 0.2s; active presses down 1px with a 0.12s `cubic-bezier(.2,.8,.2,1)`.
- **Done:** the button fills with lamp amber (`#ffe08a` → `#ffd166`), text flips to near-black, and the label changes to "Copied" for 1.8s before reverting. This is the system's success state — a light coming on, not a green tick.
- **Focus:** a 3px Safety Red outline at 3px offset, switching to lamp amber on the rail, the chest, the footer, and on any copy button.

### Cards / Containers
There are no cards. Content sits on one of four materials:
- **Paper note** — two-stop warm paper gradient, square corners, taped at the top centre, 16px 20px 14px padding. Carries the lede and the shop-rules preamble.
- **Inventory sheet** — Shop Paper, square corners, two push pins, rotated `-0.25deg`, 36px 24px 24px padding. Un-rotates below 760px. A `.flat` variant keeps the paper and drops the rotation for in-column use.
- **Drawer front** — red steel gradient panel, 4px radius, 18px 24px padding, on the dark chest ground. Carries a paper name label (Shop Paper chip, display 800 uppercase at 1.25rem), a mono count, one paragraph of copy, and a chrome pull.
- **Engraved plate** — brushed aluminium gradient, 3px radius, two radial-gradient screw heads pinned at the left and right edges, engraved text (dark ink with a white 1px text-shadow), and the amber halo. Reserved for the install command.

### Inputs / Fields
No text inputs exist. The only interactive control besides buttons is the **hang switch**: a 54×26 recessed track in dark red, a 20px chrome ball, and a 0.28s `cubic-bezier(.2,.9,.2,1.1)` throw of 28px. When checked the ball becomes lamp amber and the "Hung" label lights amber; unchecked, "Empty" is the lit label. It is a real `role="switch"` with `aria-checked`, flanked by mono capital labels.

### Navigation
The red steel rail is the only navigation. Brand wordmark in display 900 at 2.1rem, embossed into the steel with a two-direction text-shadow (`0 1px 0 #ff8a95, 0 -1px 0 #5a0710`), a mono sub-label beside it, a centred mono harness list with 6px white dot bullets, then the switch and the plate. Sticky at the top on desktop, static below 760px where it restacks to a single column and drops the harness list. Links are inherited-colour with a 1.5px underline at 0.2em offset; on paper they take Safety Red.

### Tool Cell (signature)
The unit the whole page is made of. Each cell is a hook, a silhouette, a stamped name and a numeral, stacked centred in a 168×240 area with no gap to its neighbours.
- **Resting (painted):** silhouette body and grip both Shadow Paint, holes knocked through to Hardboard, tight painted shadow. The name is mono capitals in Ink on a knock-out plate; the count is display 700 at 0.9rem in Ink Soft.
- **Hover / focus / open:** the silhouette lifts `translateY(-4px) rotate(-2deg)` over 0.5s `cubic-bezier(.2,.9,.2,1)` and the name turns Safety Red. The whole cell is one button with `aria-expanded`.
- **Hung:** three custom properties swap — body to Tool Steel, grip to Grip Red, shadow to the deeper object shadow — and each silhouette plays a 0.6s `cubic-bezier(.2,1.1,.3,1)` drop with a 45ms-per-index stagger, so the board fills left to right. Under `prefers-reduced-motion` the drop is removed and the state change is instant.

### Inventory Tag (signature)
The punched paper tag that reads out a tool. Clipped top-right corner, circular eyelet, skill name in display 800 uppercase, the SKILL.md description in 0.92rem body, then a bottom row carrying the display-face use count with a mono caption, the tool's shop name in mono capitals, and a red link. On desktop it is pinned to the bottom right of the board in a zero-height sticky layer and fades in with a 0.25s opacity / 0.35s translate reveal; below 760px the sticky layer collapses and the tag becomes a permanently visible in-flow card beneath the board. It answers hover, focus and click, and Escape closes it.

### Inventory Table
Mono capital headers at 0.66rem with 0.08em tracking over a 2px Ink rule; rows separated by 1px `rgba(21,20,18,.18)`; first column mono at 0.76rem with a 1.5px red underline on the link; last column display 800 tabular numerals, right-aligned, dropping to 0.9rem in Ink Soft when the count is zero; row hover tints `rgba(192,17,31,.06)`. Below 760px the header row is hidden and each row becomes a 2-column grid card with the numeral spanning both rows on the right.

### Numbered Steps
An ordered list with upper-roman counters in display 900 at 2.4rem, a 64px counter column, and 2px Ink rules above every item and below the last. Each step carries a title, one paragraph, and a full-width command block in reversed mono on Shadow Paint with its own copy button.

## Do's and Don'ts

### Do:
- **Do** size everything from the 24px cell, because the cell is visible as the hole lattice behind the page.
- **Do** put a Hardboard knock-out plate behind any text that lands on the perforations.
- **Do** build raised surfaces as a gradient plus a 1px top highlight and a dark bottom lip, with the cast shadow offset down and right.
- **Do** keep every label in mono capitals with 0.03–0.08em tracking, and every heading in display capitals at 800–900.
- **Do** set body copy only on a paper surface, with an explicit `ch` measure.
- **Do** change material to show state — paint to steel, tight shadow to deep shadow — rather than changing opacity.
- **Do** switch the focus ring from Safety Red to lamp amber whenever the focused control sits on red or dark ground.
- **Do** label any number shown on the board with what it counts and over what window, in mono beside the numeral.
- **Do** keep tool art on the shared 120×220 frame at one displayed scale.
- **Do** cancel the drop animation and the tag's transition under `prefers-reduced-motion`, keeping the end state.

### Don't:
- **Don't** let a second element glow. The amber bloom belongs to the engraved plate alone.
- **Don't** round a paper surface or square off a grip; the radius is the material.
- **Don't** introduce grid gap between tool cells — the lattice is the gutter.
- **Don't** dim text or drop opacity to express an inactive state.
- **Don't** set Martian Mono as running text or below 0.58rem; it is a stamping face.
- **Don't** put a type size between 1.5rem and 2.2rem into the ramp; the middle register is body copy on paper only.
- **Don't** scale a tool up to signal importance — the use count carries weight, the silhouette does not.
- **Don't** introduce a second accent hue. Red is structure and amber is light; a third colour has no material to stand on.

## Open Opportunities

Recorded from the finish review as headroom, not as rules. None of these is built; the page shipped without them.

- **The empty hook is never shown.** The board always presents 23 occupied positions. A vacant hook or an unpainted shadow — a tool checked out, a skill not installed — would make the "empty vs hung" story literal instead of purely tonal.
- **Labels are plain mono capitals, not stencil ink.** The OWN-WORLD brief calls for stencil-ink labels; the build stamps clean Martian Mono on a knock-out plate. A sprayed or bridged stencil treatment for tool names is unclaimed territory.
- **The board has no frame or edge trim.** The hardboard runs to the viewport edge with no capping rail, batten or fixing screws at its perimeter, so the board reads as a texture rather than as a mounted panel.
- **Hung tools carry no specular or wear detail.** The hung state is flat steel and flat grip red with no highlight, scuff or edge light, which is why it reads as a colour swap more than as a material change.
