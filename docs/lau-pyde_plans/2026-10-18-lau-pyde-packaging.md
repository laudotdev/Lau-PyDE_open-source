# Lau-PyDE Packaging and Update Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare Lau-PyDE 1.1.0 for reliable update checks and organized Windows, Arch Linux, and generic Linux distribution workflows.

**Architecture:** Keep the existing PySide6 updater and installer mechanisms. Add focused platform subdirectories and documentation, while using GitHub Releases for metadata and verified website links only when available.

**Tech Stack:** Python, PySide6, urllib, pytest, Bash, PKGBUILD, PyInstaller/Inno Setup documentation.

**Spec:** User-provided Lau-PyDE v1.1.0 master implementation prompt.

## Global Constraints

- Current intended version is `1.1.0`.
- Existing published releases must not be deleted, overwritten, or retagged.
- No invented website URLs, automatic installers, package-manager execution, or `git pull`.
- Commit messages must be lowercase.
- Do not claim Windows builds or website deployment without verification.
- Avoid separator comments such as `#====`.

## Review Focus

- Prefixed release tags normalize to numeric semantic versions.
- Missing platform assets fall back to a verified release page.
- Startup checks remain quiet and throttled.
- Installer updates preserve user settings and projects.
- Windows documentation distinguishes Arch-side preparation from Windows-only validation.

### Task 1: Release tag normalization

**Files:**
- Modify: `core/update_checker.py`
- Test: `tests/test_update_checker.py`

- [ ] Add failing tests for `Lau-PyDE_v1.0`, `Lau-PyDE_v1.0.0`, `v1.0`, and standard tags.
- [ ] Run focused tests and verify failure.
- [ ] Normalize supported prefixes and missing patch components.
- [ ] Run focused and full tests.
- [ ] Commit with a lowercase message.

### Task 2: Organized installer layout

**Files:**
- Create: `installer/windows/`, `installer/arch/`, `installer/linux/`
- Modify: installer documentation and scripts as needed.
- Test: shell syntax and package metadata checks.

- [ ] Move or add only platform-specific files without changing installation behavior.
- [ ] Validate scripts and package metadata.
- [ ] Commit with a lowercase message.

### Task 3: Windows installer preparation

**Files:**
- Create or modify Windows build documentation/configuration only if supported by the repository.
- Test: static validation available on Arch.

- [ ] Document PyInstaller/Inno Setup prerequisites, output naming, license, launch option, and Windows-only validation.
- [ ] Do not claim a Windows build.
- [ ] Commit with a lowercase message.

### Task 4: Platform download routing and tests

**Files:**
- Modify: `core/update_checker.py`, `ui/main_window.py`
- Test: `tests/test_update_checker.py`

- [ ] Route only to verified destinations and use safe fallbacks.
- [ ] Add mocked platform-routing and error tests.
- [ ] Run the complete suite.
- [ ] Commit with a lowercase message.

### Task 5: Release documentation

**Files:**
- Modify: `installer/README.md`, `README.md`

- [ ] Document reproducible release and validation commands.
- [ ] State unavailable Windows and website steps explicitly.
- [ ] Run final verification.
- [ ] Commit with a lowercase message.
