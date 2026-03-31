# MaestrIA — Claude Code + Higgsfield Workflow

## Project Overview

MaestrIA produces cinematic AI content (images & videos) for brands using Higgsfield.
This file defines how Claude should behave during every session.

---

## Tools

| Task | Tool |
|------|------|
| Image generation | Higgsfield NanoBanana Pro |
| Video generation | Higgsfield Cinema Studio |
| Browser control | Playwright MCP |

---

## Default Settings

```
Aspect ratio:   16:9
Image count:    8 per prompt
Resolution:     2K Unlimited ON
Extra free gens: OFF
```

---

## Folder Structure

```
MaestrIA/
  CLAUDE.md
  index.html
  reference/     ← brand references, mood boards
  images/        ← generated images, organized by client/date
  videos/        ← generated videos, organized by client/date
  output/        ← final curated assets ready for delivery
```

---

## Workflow

### Standard Content Pack

1. Receive client brief (brand, style, mood)
2. Generate 3–5 prompts based on brief
3. **Show prompts to user — wait for confirmation before generating**
4. Open Higgsfield NanoBanana Pro via Playwright
5. Set default settings (16:9, 2K Unlimited ON)
6. Generate images (8 per prompt)
7. Save outputs to `images/<client>/<date>/`
8. User selects best images
9. Generate videos from selected images using Cinema Studio
10. Save outputs to `videos/<client>/<date>/`
11. Move final curated assets to `output/<client>/`

### Pack Tiers

| Pack | Images | Videos | Reels |
|------|--------|--------|-------|
| Esencial ($897 MXN) | 10 | 3 | — |
| Cinemático ($1,499 MXN) | 15 | 6 | — |
| Director ($2,797 MXN) | 20 | 9 | 4 |

---

## Rules

- **Never generate without explicit confirmation.** Always show prompts first.
- Keep all assets organized in the folder structure above.
- Label files clearly: `client_style_v1.png`, `client_scene01_v1.mp4`
- When in doubt about style direction, ask before generating.
- Log what was generated: client, prompts used, settings, date.

---

## Higgsfield Navigation

```
NanoBanana Pro:    higgsfield.ai → Image → NanoBanana Pro
Cinema Studio:     higgsfield.ai → Video → Cinema Studio
```

After opening Higgsfield, always verify settings before starting.

---

## Prompt Style Guide

Cinematic prompts should include:

- **Subject** — what/who is in the scene
- **Lighting** — cinematic, golden hour, studio, etc.
- **Mood** — dramatic, editorial, minimal, luxury
- **Camera** — wide shot, close-up, aerial, etc.
- **Brand tone** — derived from client brief

Example:
```
Close-up of artisan coffee cup, steam rising, golden hour light,
dark editorial background, luxury brand aesthetic, 8K cinematic
```

---

## MCP Requirements

Playwright MCP must be active. Verify with `/mcp` — you should see `playwright`.

If missing, run:
```
claude mcp add playwright npx '@playwright/mcp@latest'
```
Then restart Claude.
