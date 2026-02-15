# Loofi Fedora Tweaks v41.0.0 "Coverage" Release Announcement

## TL;DR

Loofi Fedora Tweaks v41.0.0 "Coverage" is now available. This is a pure test and CI release with zero production code changes -- coverage pushed from 74% to 80%+.

**Install now:**

```bash
pkexec dnf copr enable loofitheboss/loofi-fedora-tweaks && pkexec dnf install loofi-fedora-tweaks
```

**GitHub Release:** https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v41.0.0

---

## What's New in v41.0.0 "Coverage"

### Test Coverage Milestone

- Coverage raised from 74% to 80%+ (30,653 statements, 6,125 missed)
- 23 test files created or expanded (~1,900 new tests)
- Total test suite: 5,894 tests collected

### CI Pipeline Hardening

- `dorny/test-reporter` renders JUnit XML as GitHub check annotations
- RPM post-install smoke test gates every release build
- Coverage threshold bumped from 74 to 80 across all CI workflows

---

### Recent Release Highlights (still included)

### v40.0.0 "Foundation"

Security hardening -- subprocess timeout enforcement, shell injection elimination,
privilege escalation cleanup, 141 silent exception blocks fixed.

### v39.0.0 "Prism"

Services layer migration -- zero deprecated imports, zero inline styles,
zero DeprecationWarnings.

### v38.0.0 "Clarity"

UX polish -- Doctor tab rewrite, theme correctness, Quick Actions wiring,
undo button, toast notifications, output toolbar, risk badges.

---

## Installation & Usage

**Fedora 43 (via COPR):**

```bash
pkexec dnf copr enable loofitheboss/loofi-fedora-tweaks
pkexec dnf install loofi-fedora-tweaks
```

**GUI Mode (default):**

```bash
loofi-fedora-tweaks
```

**CLI Mode:**

```bash
loofi-fedora-tweaks --cli info
loofi-fedora-tweaks --cli health
loofi-fedora-tweaks --cli doctor
```

**Headless Web API:**

```bash
loofi-fedora-tweaks --web
```

---

## Stats

- **Tests**: 5,894 collected
- **Coverage**: 80%
- **Test files**: 193
- **Tabs**: 28
- **Utils modules**: 106

---

## Links

- **GitHub Release**: https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v41.0.0
- **Full Changelog**: https://github.com/loofitheboss/loofi-fedora-tweaks/blob/master/CHANGELOG.md
- **Documentation**: https://github.com/loofitheboss/loofi-fedora-tweaks#readme
- **Report Issues**: https://github.com/loofitheboss/loofi-fedora-tweaks/issues

---

**Credits:**
- Developed with assistance from Claude Code (Anthropic)
- Built for the Fedora Linux community
- Open source under MIT License

**Maintainer:** Loofi ([@loofitheboss](https://github.com/loofitheboss))
