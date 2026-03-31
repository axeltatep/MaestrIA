# MaestrIA — Claude Code Workflow

## Project
MaestrIA produces cinematic AI content (images + videos) for brands using Higgsfield.

---

## Tools

Image generation:
Higgsfield NanoBanana Pro

Video generation:
Higgsfield Cinema Studio

Browser control:
Playwright MCP

---

## Default Settings

Aspect ratio:
16:9

Image count per prompt:
8

Resolution:
2K unlimited ON

Extra free gens:
OFF

Output format:
MP4 (video), PNG (image)

---

## Workflow

1. Open Higgsfield with Playwright
2. Set model and default settings
3. Enter prompt (show to user before generating)
4. Wait for user confirmation before generating
5. Generate images
6. User selects best images
7. Generate video from selected images
8. Download and save to /output folder
9. Organize: images → /images, videos → /videos, refs → /reference

---

## Folder Structure

```
MaestrIA/
  CLAUDE.md
  reference/   ← brand references, mood boards
  images/      ← generated images
  videos/      ← generated videos
  output/      ← final approved assets
```

---

## Style Guidelines

Always aim for:
- Cinematic lighting (golden hour, studio soft light, neon)
- Shallow depth of field
- 35mm film grain or hyperrealistic 8K
- Dark moody aesthetic or brand-specific palette
- Specific camera movement (dolly, slow motion, aerial)

---

## Rules

- NEVER generate without showing prompts first
- ALWAYS wait for user confirmation before generating
- ALWAYS use 16:9 unless user specifies otherwise
- ALWAYS save outputs to the correct folder
- If unsure about a prompt, ask before proceeding

---

## Quick Commands

Generate product images:
```
Generate 8 cinematic product images using NanoBanana Pro, 16:9.
```

Generate video:
```
Generate a cinematic video using Cinema Studio from the selected image.
```

Test browser:
```
Use playwright to open higgsfield.ai
```

Check MCP:
```
/mcp
```
