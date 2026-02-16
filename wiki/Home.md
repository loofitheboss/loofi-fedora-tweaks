# Loofi Fedora Tweaks Wiki

Welcome to the official wiki for **Loofi Fedora Tweaks** — a comprehensive desktop control center for Fedora Linux.

## About

Loofi Fedora Tweaks is a PyQt6-based system management application that brings together day-to-day maintenance, diagnostics, tuning, networking, security, and automation in one unified interface.

**Current Version**: v42.0.0 "Sentinel"

### Key Features

- **29 feature tabs** organized into 8 activity-based categories
- **4 run modes**: GUI (default), CLI with `--json` output, Daemon scheduler, and Web API
- **Plugin architecture** with marketplace support for third-party extensions
- **Atomic Fedora aware**: Auto-detects Traditional Fedora (`dnf`) vs Atomic Fedora (`rpm-ostree`)
- **Secure privilege escalation**: All root operations use `pkexec` (Polkit), never `sudo`
- **Comprehensive test suite**: 5895 tests with 82% coverage

> **Note**: Before using the automatic wiki publishing workflow, you must enable the Wiki feature in your repository settings (Settings → Features → Wikis). The first push may fail if the wiki hasn't been initialized.

---

## Wiki Pages

### Getting Started

- **[Installation](Installation)** — System requirements, installation methods (Quick Install, RPM, from source)
- **[Getting Started](Getting-Started)** — First-run wizard, GUI navigation, CLI basics
- **[FAQ](FAQ)** — Frequently asked questions

### Features & Usage

- **[GUI Tabs Reference](GUI-Tabs-Reference)** — Complete reference for all 29 tabs organized by category
- **[CLI Reference](CLI-Reference)** — All CLI commands with examples and JSON output
- **[Configuration](Configuration)** — Config files, themes, QSS styling, app catalog

### Architecture & Development

- **[Architecture](Architecture)** — Project structure, layer rules, critical patterns
- **[Plugin Development](Plugin-Development)** — Plugin SDK guide, marketplace publishing
- **[Security Model](Security-Model)** — pkexec policies, audit logging, parameter validation
- **[Atomic Fedora Support](Atomic-Fedora-Support)** — Detection, behavioral differences, developer rules

### Contributing & Support

- **[Contributing](Contributing)** — Development setup, coding standards, PR workflow
- **[Testing](Testing)** — Test suite metrics, running tests, testing patterns
- **[CI/CD Pipeline](CI-CD-Pipeline)** — Pipeline files, auto-release flow, manual releases
- **[Troubleshooting](Troubleshooting)** — Quick diagnostics, common issues, support bundle

### Reference

- **[Changelog](Changelog)** — Version history highlights from v25.0.0 to v42.0.0

---

## Quick Links

- **GitHub Repository**: [loofitheboss/loofi-fedora-tweaks](https://github.com/loofitheboss/loofi-fedora-tweaks)
- **Latest Release**: [v42.0.0](https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v42.0.0)
- **Issues**: [Issue Tracker](https://github.com/loofitheboss/loofi-fedora-tweaks/issues)
- **README**: [Main README](https://github.com/loofitheboss/loofi-fedora-tweaks/blob/master/README.md)
- **Architecture Doc**: [ARCHITECTURE.md](https://github.com/loofitheboss/loofi-fedora-tweaks/blob/master/ARCHITECTURE.md)

---

## Project Status

- **Latest Stable**: v42.0.0 "Sentinel" (February 2026)
- **Python**: 3.12+
- **Framework**: PyQt6
- **Platform**: Fedora 43+
- **License**: MIT

---

## Support

For bug reports, feature requests, or questions:

1. Check the [Troubleshooting](Troubleshooting) page
2. Search existing [GitHub Issues](https://github.com/loofitheboss/loofi-fedora-tweaks/issues)
3. Run diagnostic commands: `loofi-fedora-tweaks --cli doctor` and `loofi-fedora-tweaks --cli support-bundle`
4. Open a new issue with complete details (Fedora version, desktop environment, steps to reproduce, error logs)
