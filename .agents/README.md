# Shared agent instructions

Reference copies of the agent instructions used across projects:

- [`AGENTS.md`](AGENTS.md) — stack-agnostic operating rules, code readability, implementation flow,
  task-completion check, planning workspace and PR conventions.
- [`agent-workflow.md`](agent-workflow.md) — the detailed `Analyze -> ... -> Handoff` procedure
  referenced by `AGENTS.md`.

These files are **not active on their own**. They apply only after the coding agent loads them;
this repository's root `AGENTS.md` is separate and covers only this repository. Keep the split
clean: global files hold only stack-agnostic rules, and each repository's `AGENTS.md` holds its own
conventions.

## Install into Kilo Code

Kilo Code loads instruction files from its global config directory in every session. Register both
files there as separate sources so each stays independently editable.

1. Copy the two files into a directory under the global config directory. From this `.agents`
   directory on Windows:

   ```powershell
   New-Item -ItemType Directory -Path "$HOME\.config\kilo\instructions" -Force
   Copy-Item AGENTS.md, agent-workflow.md "$HOME\.config\kilo\instructions\"
   ```

   The global config directory is `%USERPROFILE%\.config\kilo\` on Windows and `~/.config/kilo/` on
   macOS and Linux.

2. Register them in `kilo.jsonc` in that config directory:

   ```jsonc
   {
     "$schema": "https://app.kilo.ai/config.json",
     "instructions": [
       "C:/Users/<you>/.config/kilo/instructions/AGENTS.md",
       "C:/Users/<you>/.config/kilo/instructions/agent-workflow.md"
     ]
   }
   ```

   Use absolute paths: the `instructions` globs are not documented as resolving relative to the
   global config directory, and `~` expansion should not be assumed. On macOS or Linux, use paths
   such as `/home/<you>/.config/kilo/instructions/AGENTS.md`.

   The same sources can be managed in the UI under **Settings → Agent Behaviour → Rules**.

3. Start a new session so the instructions are loaded; they are read at session start.

To verify, open a fresh session and ask which implementation flow it is following — it should
answer with `Analyze -> Specify -> Plan -> Implement -> Review -> Test -> Redo -> Handoff` and the
handoff/commit approval rule from `AGENTS.md`.

### Alternative: single global `AGENTS.md`

Kilo Code also auto-discovers `~/.config/kilo/AGENTS.md` without a `kilo.jsonc` entry. Copying this
directory's `AGENTS.md` there works, but the link to `agent-workflow.md` must still resolve: keep
`agent-workflow.md` in the same directory, or replace the link with an absolute path. Registering
both files through `instructions` is less error-prone.

## Keeping them in sync

Edit the files here first, then re-copy them to the agent config directory; do not edit the
installed copies independently. Links in these files are relative to this directory, so keep
`AGENTS.md` and `agent-workflow.md` together when copying them.
