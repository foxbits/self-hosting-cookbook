# AGENTS.md — shared agent instructions

These instructions are stack- and project-agnostic. They take effect only when a coding agent
loads them; see [README.md](README.md) to install them. Each repository's own `AGENTS.md` adds
project-specific conventions on top of these.

## Repository instructions

These instructions apply to the whole project. Before changing a file in a nested scope, also read
every `AGENTS.md` from the repository root to that file; the more specific instructions apply in
addition to the broader ones.

Read the project instructions and its repository map before exploring or editing. Do not read every
existing component to infer conventions when the instructions already define them; read
contextually and load only the documentation a task routes you to.

## Operating and decision rules

- Make the smallest coherent change that satisfies the confirmed request; preserve unrelated work
  and existing published behavior.
- Ask before acting on unresolved material scope, architecture, contract, data, compatibility,
  security or operational questions. Inspect available evidence without inventing requirements.
- Complete one authorized task's implementation, review and focused validation before presenting
  its concrete result. Pause before another task unless continuation is explicitly authorized.
- Stage only task-owned files with `git add -- <exact-paths>`; never `git add .`, `git add -A` or a
  broad equivalent. Keep unrelated changes, local plans, credentials, diagnostics and generated
  artifacts out of the commit.
- Before handoff inspect `git status --short`, `git diff --cached --name-only` and the task-owned
  staged/unstaged diffs. Ensure every deliverable is staged and unrelated files are preserved.
- Present the exact atomic commit subject and staged change; obtain explicit approval before
  `git commit`. Push, PR and deployment actions require authorization for their concrete scope.
  Reuse authorization already given; do not request it repeatedly.
- Use a short, descriptive branch name such as `feature/<identifier>` with at most three identifier
  words. Preserve the task branch; do not force-push, reset, overwrite or delete work to simplify a
  task.
- Never expose credentials or rely on unverified environment-specific assumptions. Use `CHANGE_ME`
  placeholders and documented generation hints in committed example configuration; real values stay
  outside the repository.
- Do not bypass review gates or submit author self-approval when the project uses them.
- Do not introduce dependencies or architectural layers without a demonstrated need. Static
  validation does not prove runtime behavior or connectivity.
- Do not start services, containers or background helpers, or mutate an environment, outside the
  workflow's approved execution scope.
- Communicate concisely, outcome-first. Report evidence, limitations and actual outcomes without
  unverified success claims.

## Code readability

- Always use braces in shell control flow (`if`, `for`, `while`, `do`) even when the body is a
  single statement.
- Give non-obvious values a name at their narrowest owning scope instead of repeating inline magic
  values across files.
- Use concise, self-explanatory names that identify a value's role, especially for primitive
  values, environment variables and configuration keys.
- Preserve existing env var names, external ports, storage paths and wire/storage values when
  refactoring; they are the user's contract in their configuration and on-disk data.
- Prefer flat, explicit configuration over abstractions that hide behavior.

## Required implementation flow

For every non-trivial implementation task follow:

`Analyze -> Specify -> Plan -> Implement -> Review -> Test -> Redo -> Handoff`

Follow [Agent workflow](agent-workflow.md) for the complete procedure, decision gates,
helper-tool usage, review checklist, testing permissions, redo loop and handoff requirements.

Only a very small task meeting the workflow's strict exception criteria may omit the Specify/Plan
artifacts.

## Task-completion knowledge check

At task completion, before the final response, check whether structural or logical changes
contradict existing guidance or reveal useful missing information. Inspect only affected
instructions, documentation, specifications and skills. Propose the exact update at the narrowest
owning file, and obtain permission before making additional changes beyond the authorized task.

## Local task-planning workspace

- Task-specific planning artifacts are local, ignored and never staged or committed unless the
  project tracks them explicitly.
- Use one stable, collision-checked directory per task inside an ignored, project-local planning
  root, for example `docs/specs/YYYYMMDD-HHmmss--funny-adjective-noun/`. Add a short identifier to
  the directory name when the work is tracked elsewhere.
- Create a new directory for each task execution and reuse one only for an explicit resume. Never
  overwrite or automatically delete prior task directories.
- Use fixed filenames: `spec.md` for confirmed requirements and acceptance criteria, `plan.md` for
  the agreed approach and validation, and `tasks.md` for the execution checklist and validation
  state.
- Every non-trivial task requires an ignored `plan.md` before implementation. See the workflow for
  the strict very-small exception.

## Pull Requests

When opening a pull request, use the title format `<scope>: <Description>`, for example
`app: Document deployment manifests`. Reference a tracking issue in the description when one
exists rather than encoding it in the title.
