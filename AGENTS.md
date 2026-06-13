# Repository Guidelines

## Project Structure & Module Organization

This repository is a static HTML learning site. The root contains the entry pages: `index.html` for the cover and `toc.html` for the lesson table of contents. Lesson pages live in `lessons/` and use zero-padded numeric filenames such as `lessons/0001-three-claudes.html`. Printable or reusable reference material lives in `reference/`, for example `reference/claude-product-picker.html`. Durable images and diagrams live in `assets/`. There is no separate source/build output split; edit the checked-in HTML directly.

## Build, Test, and Development Commands

There is no package manager manifest or build script. Use local static serving when reviewing pages:

```sh
python3 -m http.server 8000
```

Then open `http://localhost:8000/` and navigate through `index.html`, `toc.html`, lessons, and reference pages. Useful inspection commands:

```sh
rg --files
git status --short
```

`rg --files` confirms the site structure. `git status --short` confirms the intended files changed.

## Coding Style & Naming Conventions

Keep pages as standalone HTML documents with embedded CSS, matching the existing pattern. Use `lang="zh-Hant"` for Chinese learning content and keep visible course prose in Traditional Chinese unless a task explicitly asks otherwise. Preserve the current indentation style: two spaces inside CSS blocks where already used, compact HTML for table-heavy pages, and readable spacing around major sections. New lessons should follow `lessons/NNNN-short-slug.html`; update `toc.html` whenever the lesson list changes.

## Testing Guidelines

No automated tests are currently configured. Verify changes by serving the site locally and checking the affected navigation path in a browser. For content changes, confirm links, lesson numbering, quiz `data-answer` values, and any referenced filenames. A relevant check should fail or visibly break if the intended lesson flow is wrong.

## Commit & Pull Request Guidelines

Recent commits use short, imperative summaries such as `Add more lesson pages` and `Update table of contents`. Follow that style: one concise sentence, capitalized, no trailing period. Pull requests should describe what content changed, list affected pages, mention manual browser checks, and include screenshots when layout or visual styling changed.

## Agent-Specific Instructions

Keep edits surgical. Do not introduce a build system, formatter, JavaScript framework, or shared CSS abstraction unless the task specifically requires it. When adding content, prefer consistency with nearby lessons over broad cleanup.
