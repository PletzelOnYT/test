# AI Development, Compilation & Testing Workspace

This repository is a dedicated workspace for AI-assisted software development, compilation, testing, debugging, and automated build execution.

## Purpose

This repository allows AI coding assistants to perform development tasks that may not be possible to complete directly within a chat environment.

It provides a GitHub-hosted environment where AI agents can:

- **Compile source code** into working applications and executable builds.
- **Run automated tests** to verify functionality and identify errors.
- **Debug and repair** compilation failures, broken dependencies, and configuration issues.
- **Execute GitHub Actions workflows** for building and testing projects.
- **Modify and integrate source code** to implement new features.
- **Install and configure dependencies** required by development tools.
- **Generate build artifacts** such as HTML files, JARs, ZIP archives, and other compiled outputs.
- **Validate completed builds** rather than relying solely on theoretical code analysis.

## AI Agent Instructions

When working with this repository, AI coding agents should:

1. Inspect the existing project structure and build configuration.
2. Identify missing dependencies, compilation errors, or incomplete implementations.
3. Make the necessary source code and configuration changes.
4. Execute available build and testing workflows.
5. Review logs, diagnose errors, and attempt corrections.
6. Repeat the build-and-test process until successful or until a documented blocker is encountered.
7. Provide the resulting artifacts and a clear summary of what was actually tested.

**Important:** This repository is intended for real development and execution, not just code generation or hypothetical solutions.

The goal is to enable AI agents with authorized GitHub access and execution tools to perform actual software engineering tasks, including compiling, testing, debugging, and producing verifiable working builds.

## Status

**AI Development & Testing Repository — Active**

## Experimental Pletzel V4 No-Voice build — 2026-11-14

The complete playable HTML is committed in the root as [Pletzel-V4-Experimental-NoVoice.html](https://github.com/PletzelOnYT/test/raw/refs/heads/main/Pletzel-V4-Experimental-NoVoice.html).

GitHub experimental prerelease: https://github.com/PletzelOnYT/test/releases/tag/pletzel-v4-easyplace-experimental-20261114

Full native compile: https://github.com/PletzelOnYT/test/actions/runs/43549286002 (successful).
Chromium eight-suite test: https://github.com/PletzelOnYT/test/actions/runs/43615183423 (6/8 passing; Easy Place and Map Art failing).
Source commit compiled: b2e5f41c87ed9d0a6645a00031d60de154bf52a2. Exact compiled HTML SHA-256: 75f229d91369e94c34550de2645c0bcb972ef5db1535d27bc3d1397afdc9c298; size: 89799848 bytes.

EXPERIMENTAL/UNVERIFIED: Do not use automated Easy Place on public multiplayer servers; potential kicks/bans and ghost blocks. Map Art persistence after a browser restart has not passed.

Previous main HTML is preserved unchanged as Pletzel-V4-Optimized-Litematica-EasyPlace-EasyPick-MapArt-NoVoice.html and also copied to backups/Pletzel-V4-main-before-2026-11-14.html. No voice chat in this release.
