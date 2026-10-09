# Version control and publication workflow

## Initial preparation boundary (historical)

This is a source-only candidate prepared on 2026-10-09. It is not an upstream CE-QUAL-W2 release or an Ubuntu-qualified binary distribution. Its source-only publication was approved for a new `linux-port` branch and draft pull request on 2026-10-09. The user-nominated destination is [chrisparsons-ECCC/CE-QUAL-W2-Linux](https://github.com/chrisparsons-ECCC/CE-QUAL-W2-Linux). Repository metadata checked during preparation identifies an existing public repository with default branch `v4.5`. Its existing history and files must be preserved. The intended account and access were verified separately. Confirm the final reviewed bytes and current base before executing that approved publication. A successful Git installation or an authenticated GitHub connector does not demonstrate shell Git push authentication or write permission for a particular repository.

The package deliberately contains no `.git` directory. Do not import a previous workspace's Git objects, reflogs, raw vendor logs, compiler recovery archives or credentials. Treat this reviewed directory as a standalone export. For the approved publication, integrate it as a clearly scoped new subtree in the existing repository, preferably `linux-port/`, after checking that destination for conflicts. Do not initialize an unrelated repository and force it over the destination. Do not use `git add .` over an investigation workspace.

## Published state and subsequent changes

The initial candidate integration is published at commit `9c16db8e7697ffaa12f9678f15329fa0ce80d872` on `linux-port`, with [draft pull request #1](https://github.com/chrisparsons-ECCC/CE-QUAL-W2-Linux/pull/1) against `v4.5`. The preparation and initial-integration instructions above and below describe that preserved history and the safeguards for later work; they are not a claim that publication is still pending.

Subsequent approved changes must use the verified current `linux-port` tip as their parent and preserve the existing files/history. Documentation corrections are genuine new commits, not rewrites of old test records. The dated evidence update records separate Ubuntu 26.04 reproduction, DeGray coverage closure and corrected Spokane bounds without changing source, tools, inputs, control hashes, FP settings, package `VERSION`, or the draft status. Application acceptance and any merge/default promotion remain separate decisions.

## Repository layout

- `source/strict/`: hash-pinned original Linux port, including its existing platform boundary changes; this is the default build profile.
- `source/windows-compatible-invalid-only/`: independently hash-pinned opt-in compatibility candidate.
- `source/helper/`: the narrowly scoped floating-point-state helper.
- `config/`: source manifests, compiler/runtime identity, build profiles and explicit publication allowlist.
- `cases/`: case input names, hashes and coverage declarations; input payloads are supplied separately.
- `tools/` and `tests/`: build/run/verification tools and unit tests.
- `docs/`, `provenance/` and `notices/`: reviewable documentation, sanitized compact evidence and applicable notices.

Build trees, case runs and full numerical output collections belong outside the repository. Keep a private artifact inventory with their content hashes and access-controlled storage locations. Public evidence uses hashes and descriptive artifact names, never private download links or account-specific workspace locations.

## Honest history in the existing repository

The live repository metadata checked on 2026-10-09 identified `v4.5` commit `5544026e3f1a39c0c9e827bd3dc2bbc13a94636c` and root tree `d2bfbf8bc93946db19e70c72ba0a04239b950997`. The new `linux-port` branch was absent at that check. The existing root `LICENSE.md` is the ERDC MIT notice and must remain unchanged. These are observed base identities, not a claim that the uploaded May 4.5.5 source matches that upstream tree.

Before integration, resolve and record the exact current `v4.5` base commit and tree, and inspect the intended subtree and relevant existing documentation. Preserve the actual upstream-derived history. Use a new approved branch and genuine new commits whose parent is the verified existing base; do not force-push, orphan the branch or manufacture historical commits.

The first candidate-integration commit can be named `Add reviewed CE-QUAL-W2 4.5.5 Linux candidate snapshot`. Its actual author, date, parent and changed files describe the integration performed now. Earlier development and experiment dates belong in this package's provenance document, clearly distinguished from newly executed tests. The package's adopted uploaded solver still has no verified matching upstream release commit; adding it to an existing repository does not establish that match.

Keep the original root README and upstream source layout intact unless a reviewed, authorized narrow change is needed, such as a link to `linux-port/README.md`. Do not silently replace the root's upstream license with a package-specific notice. Preserve existing files by starting from the verified base tree and adding only reviewed paths. Do not read or import prohibited raw vendor/debug logs or old investigation Git metadata. The safe publication unit is the new reviewed delta; the content scanner does not certify pre-existing repository history.

Do not recreate old commits with invented parents, timestamps, signatures or author identities. Do not import old workspace Git objects to make the port appear to have a recovered history. After integration, make small genuine commits for each completed logical change, identifying affected profiles, evidence and tests. Keep numerical changes, packaging changes and documentation changes separately reviewable. Preserve source notices.

## Exact bytes, staging and review

`.gitattributes` disables newline conversion and content filters for this package. The existing mixed-case filenames, spaces and original line endings are intentional: the source manifests hash raw bytes. Never run a blanket formatter or newline-normalization command over the frozen source.

Before a commit or export:

1. Run `python3 tools/publication_preflight.py` from the clean package. It checks the worktree against `config/publication-allowlist.json`, source hashes and a bounded secret/private-link scan. It refuses unknown files, symlinks, binary payloads and raw logs before reading their contents.
2. Stage only the reviewed explicit paths. Adding a new file requires an explicit allowlist edit and review.
3. Run `python3 tools/publication_preflight.py --git-index` for a standalone repository. When integrated under `linux-port/`, run it from that package with `--git-index --repo-root ..`. The explicitly named Git root is checked, and only staged package blobs are read. Independently review every other changed repository path, such as a root README link. A clean worktree scan alone cannot establish staged-byte safety.
4. Review staged path names, diff/stat, permissions, license notices, test status and author identity. Check for staged deletions or unrelated content. Do not print entire sensitive diffs into review logs.
5. Run the applicable aggregate tests against the final bytes. Build and run receipts must identify the profile and hashes. A documentation-only change need not imply a new numerical qualification.

When using a GitHub tree/commit API instead of a local index, scan the exact outgoing package bytes, preserve the verified base tree, and verify each new remote blob/hash plus the changed-path list before declaring equivalence. Do not substitute a mutable worktree scan for that outgoing-byte review.

The scanner is a guardrail, not exhaustive secret detection, legal clearance or permission to publish. `.gitignore` does not remove already tracked files; a secret in any commit reachable from a pushed branch remains a publication risk even if later deleted. This package's staged scan does not audit historical Git objects.

## Controlled remote publication, once authorized

Confirm the exact existing repository, visibility/audience, branch and intended content. Resolve the existing `v4.5` base commit immediately before branch creation, retain it as the actual new commit parent, and inspect any existing destination subtree. If the proposed working branch already exists, inspect its current tip and changes before integrating; do not force-push or replace unrelated history. Keep creation of a new repository, remote publication and public visibility changes explicit.

Use the approved GitHub connector or an already authorized Git transport. Never place a token in a remote URL, script, command-line argument, commit, build receipt or chat message. Persistent credential creation/configuration requires its own approval; this package does not perform it. A read-only remote check and a dry run can diagnose access but do not prove the actual push succeeded.

Push only the approved branch/ref, without `--mirror`, `--all` or implicit tag publication. Verify the remote branch tip equals the intended full commit ID and inspect any CI run for that exact commit. Report the verified commit/link and any failed or unrun checks. Tag only an approved, reviewed snapshot, with names such as `port-v0.1.0-rc.1`; do not use an unqualified upstream-looking `v4.5.5` tag.

For a source archive, export only the reviewed package subtree from the approved commit, verify its contents again, and attach a file manifest and archive SHA-256. A Git archive identifies a tree/commit; it does not establish test results or publication rights. This document describes the workflow; a publication is complete only when its final remote commit, changed paths and draft pull request have been independently verified.

## References

- [Git attributes and byte conversion](https://git-scm.com/docs/gitattributes)
- [Git ignore behavior](https://git-scm.com/docs/gitignore)
- [Inspecting the index](https://git-scm.com/docs/git-ls-files)
- [Git archive behavior](https://git-scm.com/docs/git-archive)
- [Git push ref selection](https://git-scm.com/docs/git-push)
