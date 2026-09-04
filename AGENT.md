# Agent Instructions

## Code style

- Use a maximum line length of **120** characters, not 80. Prefer wrapping only when a line would exceed 120.
- In code and comments, stick to plain ASCII. Do not use em dashes, en dashes, smart quotes, rightward arrows, or other Unicode characters above ASCII.
- Do not remove previous user-written comments unless the meaning of the current change really conflicts with them. Separator comments (e.g. `# ----`, `# --`) are for user readability; keep them during refactors and other edits.
- In code comments, write only the current meaning or constraint. Do not leave editorial comments, correction notes, changelog asides, "fixed this", "was X now Y", review remarks, or similar meta-commentary.

## Secrets and env files

- Never read, edit, or print `.env` / `.env.*` files.
- Use `.env.example` for variable names only.
- Never run `cat` / `head` / `grep` / `printenv` on env files or secret vars.

## Tests

- Do not create new tests unless the user specifically asks for them. New test files or new test cases burn tokens and are not wanted by default.
- You may update existing tests when they conflict with new logic. Do not add extra coverage while doing so.

## OpenAPI

- When editing an OpenAPI spec, write only the final developer-facing contract: concise descriptions, field meanings, constraints, and examples. Do not leave editorial comments, correction notes, changelog asides, "fixed this", "was X now Y", review remarks, or similar meta-commentary in descriptions or YAML comments.
