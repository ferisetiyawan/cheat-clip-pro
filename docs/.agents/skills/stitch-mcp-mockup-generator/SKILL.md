---
name: stitch-mcp-mockup-generator
description: Use this when the user wants to generate actual Google Stitch mockups/screens directly from a PRD via a connected Stitch MCP server — no manual prompt copy-pasting into stitch.withgoogle.com. Always asks which platform(s) to mock up first (Mobile app, CMS/admin dashboard, Customer web, any combination, or others the user names), and creates a separate Stitch project per platform so design systems don't mix. Trigger on "generate the mockup through MCP," "use Stitch MCP," "create the screens directly," or "skip the copy-paste" when a PRD (ideally from ai-friendly-prd) is available. Requires an MCP-capable agent (Claude Code, Cursor, Gemini CLI, VS Code, Codex, OpenCode) with Stitch MCP configured — does NOT work in claude.ai web/mobile chat, which has no Stitch connector. If no Stitch MCP tools are visible, tell the user this needs Claude Code (or similar) with Stitch MCP set up, rather than falling back to plain-text prompts silently.
---

# Stitch MCP Mockup Generator

## Reality check before using this skill

Google Stitch's MCP integration is a **local/IDE integration**, not a claude.ai connector. It's configured per-machine via a CLI (commonly `@_davideast/stitch-mcp`, or the official `gemini-cli-extensions/stitch` extension) that authenticates against a Google Cloud project and exposes Stitch's tools to a coding agent (Claude Code, Cursor, Gemini CLI, VS Code, Codex, OpenCode).

**Before doing anything else, check the actual tool list available in this session.** If tools like `generate_screen_from_text`, `create_project`, `list_projects`, `get_screen`, `get_screen_code`, or `get_screen_image` are present, proceed. If none are present:
- Don't fabricate calls or pretend to generate mockups.
- Tell the user plainly: this needs the Stitch MCP server connected in an MCP-capable agent (Claude Code, Cursor, etc.), and point them to `references/stitch-mcp-setup.md` for setup steps.
- Offer the `stitch-prompt-generator` skill instead (produces copy-paste prompts) as the fallback for this session.

## What the connected tools typically do

Exact tool names/parameters can vary slightly by which Stitch MCP implementation the user has installed, so inspect the live tool schema rather than assuming — but the common set is:

- **`create_project`** — starts a new Stitch project (a project groups related screens so they share a design system).
- **`list_projects`** / **`get_project`** — find an existing project instead of creating a new one, if the user already has one for this product.
- **`generate_screen_from_text`** — the core generation call: takes a text prompt (and a project id) and returns a new screen.
- **`list_screens`** / **`get_screen`** — inspect screens already generated in a project.
- **`get_screen_code`** — downloads the generated HTML/CSS for a screen.
- **`get_screen_image`** — downloads a screenshot (often base64) of a screen for quick visual review.
- **`build_site`** (proxy-only, in some implementations) — maps multiple screens to routes and assembles them into one buildable site.

## Workflow

### 1. Ask which platform(s) to generate mockups for
Always ask this before touching Stitch — never assume "mobile" or "web" from the PRD alone, since a PRD's Requirements section describes the product's accessibility constraints, not necessarily which distinct front-ends the person wants mocked up. Offer, at minimum:
- **Mobile app** (end-user-facing, native/mobile-web)
- **CMS** (internal admin/staff/operations dashboard — the back-office side)
- **Customer web** (end-user-facing, browser/desktop)
- Any combination of the above, or additional platforms the person names (e.g. a public marketing site, a partner portal) that aren't in this default list

Ask this directly in conversation (this skill runs in a coding-agent environment without a UI picker) — list the options plainly and wait for an answer before creating anything in Stitch. The person may want just one, two, or all three (or more), and getting this wrong means regenerating everything against a fresh project later. If the PRD already implies certain roles map to certain platforms (e.g. Tenant → mobile, Manager/Staff/Security → CMS), mention that mapping as a suggested default in the question, but still let the person confirm or override it.

### 2. Create one **separate Stitch project per selected platform**
This is deliberate and non-negotiable: each platform gets its own `create_project` call and its own project id, never a shared project. Mixing a mobile app's screens and a CMS dashboard's screens into one Stitch project means they share one design system and generation context — which is exactly what causes an AI coding agent to blend mobile-nav patterns into a desktop dashboard (or vice versa) later when it reads the exported code. One project per platform keeps each self-contained and unambiguous downstream.

Name each project clearly and consistently, e.g. `[Product Name] — Mobile`, `[Product Name] — CMS`, `[Product Name] — Customer Web`. Before creating, check `list_projects`/`get_project` in case a project for that platform already exists for this product — reuse it instead of creating a duplicate.

Keep a running map of `platform → project id` for the rest of this workflow — every subsequent tool call needs the *correct* project id for the screen it's generating.

### 3. Parse the PRD into a screen list, tagged by platform
Same extraction logic as `stitch-prompt-generator`, with one addition — every screen must be tagged with which selected platform it belongs to (a feature can produce screens on more than one platform, e.g. "Facility Booking" often means a tenant-facing booking screen on Mobile *and* a staff-facing management view on CMS — these are two screens in two different projects, not one):
- **Requirements section** → confirms/refines the platform note for each role, and any layout-relevant constraints per platform.
- **Core Features section** → the screen list. Split any feature that implies multiple screens (e.g. a list view + an add/edit form are 2 screens), and split further if a feature spans more than one selected platform.
- **User Flow section** → generation order per platform, so later screens can reference earlier ones for consistency within that platform's project.
- **Database Schema section** → exact field names to use in prompts for any form/table screen — never invent field names the schema doesn't have.
- **Design & Technical Constraints** → color/typography/style directives to fold into every prompt; note if the person wants a distinct visual identity per platform (common — a CMS is usually denser/more utilitarian than a customer-facing app) or one consistent identity across all of them.

If the PRD isn't in this conversation yet, ask for it (paste or file path) rather than inventing screens. Only proceed to generation once every screen in your list has both a name and a platform tag.

### 4. Send one project-context prompt per platform (not one for the whole product)
Since each platform is its own project, each needs its own context-setting (if the tool schema supports a project-level prompt/context field), describing that platform's target user and visual direction specifically — a CMS's context prompt should say "internal staff dashboard, dense and data-oriented," not reuse the mobile app's "clean and approachable" framing. If the schema requires every `generate_screen_from_text` call to be self-contained instead, prepend that platform-specific context sentence to every individual screen prompt within that project.

### 5. Call `generate_screen_from_text` once per screen, into the correct project
Build each prompt using the same structure as `stitch-prompt-generator` (see that skill's `references/stitch-prompting-guide.md` for the full rules): platform stated explicitly, goal in one sentence, layout top-to-bottom, components named explicitly with real field names, and a concrete visual direction. Pass the project id from your platform→project map in step 2 — double-check you're generating each screen into the project that matches its platform tag before calling the tool. Call the tool — don't print the prompt for the user to paste, that defeats the point of this skill.

Respect generation limits: free tiers commonly cap around 350 generations/month, shared across all projects in the account. If the combined screen count across all selected platforms is large, tell the person the total up front (broken down per platform) and confirm before burning through the quota, rather than silently generating everything.

### 6. Retrieve results
After each generation, call `get_screen_code` (for the HTML/CSS, if the user wants it wired into a codebase) and/or `get_screen_image` (for a quick visual the user can review in this chat). Show the image inline where the interface supports it, or describe what was generated and where to view it (Stitch project URL, if the tool result includes one). Keep results grouped by platform when reporting back — don't merge them into one undifferentiated list.

### 7. Summarize and hand off
At the end, give the person a per-platform breakdown: each project's id/name, the screens generated in it, and — if a platform's screens should become a deployable site — offer to call `build_site` (or equivalent) to map that project's screens to routes. Keep the platforms' outputs clearly separated in this summary, matching how they're separated in Stitch.

## If something fails

Auth errors, quota errors, or missing-tool errors are common given this is an experimental integration. Report the actual error back to the user rather than retrying blindly or guessing a workaround — point them at `references/stitch-mcp-setup.md`'s troubleshooting section if it's a setup/auth issue.

## Reference files

- `references/stitch-mcp-setup.md` — how the Stitch MCP server actually gets installed and authenticated (for context if the user asks why it isn't available, or wants to set it up).
