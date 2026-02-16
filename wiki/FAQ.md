# FAQ

Frequently Asked Questions about Loofi Fedora Tweaks.

---

## General

### What is Loofi Fedora Tweaks?

Loofi Fedora Tweaks is a comprehensive system management application for Fedora Linux. It combines maintenance, diagnostics, tuning, networking, security, and automation tools in one unified interface.

**Key features:**
- 28 feature tabs organized by activity
- CLI mode with `--json` output for scripting
- Daemon mode for background automation
- Plugin marketplace for third-party extensions
- Full support for both Traditional and Atomic Fedora

---

## Compatibility

### What Fedora versions are supported?

**Supported**: Fedora 43 and later

**Minimum requirements:**
- Fedora 43+
- Python 3.12+
- PyQt6

Older versions may work but are not officially supported or tested.

### Does it work on Fedora Silverblue/Kinoite (Atomic)?

**Yes!** Loofi Fedora Tweaks fully supports Atomic Fedora variants:

- Fedora Silverblue (GNOME)
- Fedora Kinoite (KDE)
- Fedora Onyx (Budgie)
- Fedora Sericea (Sway)

The application automatically detects `rpm-ostree` and adapts all package operations accordingly.

See: [Atomic Fedora Support](Atomic-Fedora-Support)

### Does it work on other Linux distributions?

**No.** Loofi Fedora Tweaks is specifically designed for Fedora Linux. While some components may work on other RPM-based distributions (RHEL, CentOS, etc.), the application is not tested or supported on non-Fedora systems.

---

## Installation & Usage

### Do I need root access?

**For GUI/CLI usage**: No root access required. The application runs as your normal user.

**For privileged operations**: Yes, you'll be prompted for authentication via `pkexec` (Polkit) when performing privileged actions like:
- Installing/removing packages
- Starting/stopping services
- Modifying firewall rules
- Updating system configuration

The application **never runs as root** — it uses Polkit for granular privilege escalation.

### Can I use it from the terminal?

**Yes!** Loofi Fedora Tweaks has a full-featured CLI mode:

```bash
loofi-fedora-tweaks --cli <command>
```

All CLI commands support `--json` output for scripting:

```bash
loofi-fedora-tweaks --cli --json info
loofi-fedora-tweaks --cli --json health
```

**Recommended alias** (add to `~/.bashrc`):

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

See: [CLI Reference](CLI-Reference)

### Can I automate tasks with scripts?

**Yes!** Use CLI mode with `--json` output:

```bash
#!/bin/bash
# Daily maintenance script

# Check health
SCORE=$(loofi --json health | jq -r '.overall_score')

if [ "$SCORE" -lt 80 ]; then
    echo "Health score low, running cleanup..."
    loofi cleanup all
fi
```

See: [CLI Reference](CLI-Reference) → Scripting Tips

---

## Features

### What desktop environments are supported?

Loofi Fedora Tweaks works on **all Fedora desktop environments**:

- ✅ GNOME
- ✅ KDE Plasma
- ✅ Xfce
- ✅ MATE
- ✅ Cinnamon
- ✅ LXQt
- ✅ Budgie
- ✅ Sway

Some desktop-specific features (like Extensions tab) adapt based on the detected environment.

### Can I install plugins?

**Yes!** Loofi Fedora Tweaks has a plugin system with marketplace support:

**Local plugins:**
```bash
# List plugins
loofi-fedora-tweaks --cli plugins list

# Enable/disable plugins
loofi-fedora-tweaks --cli plugins enable my-plugin
loofi-fedora-tweaks --cli plugins disable my-plugin
```

**Marketplace plugins** (v27.0+):
```bash
# Search marketplace
loofi-fedora-tweaks --cli plugin-marketplace search --query backup

# Install plugin
loofi-fedora-tweaks --cli plugin-marketplace install backup-manager --accept-permissions
```

See: [Plugin Development](Plugin-Development)

### Can I develop my own plugins?

**Yes!** The Plugin SDK makes it easy to extend Loofi Fedora Tweaks:

**Quick start:**
1. Create `plugins/my-plugin/plugin.json` (manifest)
2. Create `plugins/my-plugin/plugin.py` (implementation)
3. Implement `LoofiPlugin` abstract base class
4. Provide GUI widget and/or CLI commands

**Resources:**
- [Plugin Development](Plugin-Development) — Complete SDK guide
- Example: `plugins/hello_world/` (bundled example plugin)

---

## Configuration

### Where are config files stored?

**User data**: `~/.config/loofi-fedora-tweaks/`

**Files:**
- `settings.json` — Application settings
- `favorites.json` — Favorite tabs
- `quick_actions.json` — Quick action buttons
- `audit.jsonl` — Audit log (privileged actions)
- `history.json` — Action history with undo commands
- `profile.json` — User profile from first-run wizard

**Logs**: `~/.local/share/loofi-fedora-tweaks/`

See: [Configuration](Configuration)

### How do I change the theme?

**GUI**: Settings tab → Appearance → Theme

**Options:**
- Abyss Dark (default dark theme)
- Abyss Light (light theme)

**Manual**:
```bash
# Edit config file
nano ~/.config/loofi-fedora-tweaks/settings.json

# Change "theme" field to "dark" or "light"
{
  "theme": "light"
}
```

### How do I reset to defaults?

**Full reset** (deletes all settings):

```bash
rm -rf ~/.config/loofi-fedora-tweaks/
rm -rf ~/.local/share/loofi-fedora-tweaks/
```

**Partial reset** (keeps favorites and quick actions):

```bash
rm ~/.config/loofi-fedora-tweaks/settings.json
```

The first-run wizard will appear on next launch.

---

## Testing & Development

### How many tests does the project have?

**Test suite metrics** (v40.0.0):
- **174 test files**
- **4349+ tests**
- **74% line coverage**
- **0 failures**

All tests run in CI on every PR.

See: [Testing](Testing)

### How do I run tests?

```bash
# All tests
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v

# Specific file
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_commands.py -v

# With coverage
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ --cov=loofi-fedora-tweaks --cov-report=html
```

See: [Testing](Testing)

---

## Security

### Is it safe to use?

**Yes.** Loofi Fedora Tweaks follows security best practices:

✅ **Polkit (pkexec) only** — Never uses `sudo`
✅ **Subprocess timeouts** — All operations have timeout limits
✅ **No shell injection** — Never uses `shell=True` or command strings
✅ **Audit logging** — All privileged actions logged to `audit.jsonl`
✅ **Parameter validation** — All inputs validated before execution
✅ **Plugin sandboxing** — Plugins run with restricted permissions
✅ **Regular security scans** — Bandit, pip-audit, Trivy on every PR

See: [Security Model](Security-Model)

### What data is collected?

**None.** Loofi Fedora Tweaks does not collect or transmit any user data.

**Local data only:**
- Settings stored in `~/.config/loofi-fedora-tweaks/`
- Logs stored in `~/.local/share/loofi-fedora-tweaks/`
- Audit trail in `audit.jsonl` (local file)

**No telemetry, no analytics, no external connections** except:
- Package manager operations (dnf/rpm-ostree repositories)
- Plugin marketplace (optional, only when explicitly used)
- Update checker (optional, can be disabled in Settings)

---

## Support

### Where do I report bugs?

**GitHub Issues**: https://github.com/loofitheboss/loofi-fedora-tweaks/issues

**Before reporting:**
1. Search existing issues
2. Run diagnostics:
   ```bash
   loofi-fedora-tweaks --cli doctor
   loofi-fedora-tweaks --cli support-bundle
   ```
3. Provide complete information:
   - Fedora version and desktop environment
   - Exact steps to reproduce
   - Expected vs actual behavior
   - Error logs (from support bundle)

See: [Troubleshooting](Troubleshooting)

### How do I request a feature?

**GitHub Issues** with `feature` label.

**Include:**
- Problem description (what user problem does this solve?)
- Proposed solution (UX/CLI behavior)
- Alternatives considered
- Additional context (screenshots, examples)

**Or develop it yourself:**
- [Contributing](Contributing) — Development guide
- [Plugin Development](Plugin-Development) — Create a plugin

### Where can I get help?

1. **Wiki**: You're already here! Browse other pages for detailed guides.
2. **Troubleshooting**: [Troubleshooting](Troubleshooting) page
3. **GitHub Issues**: https://github.com/loofitheboss/loofi-fedora-tweaks/issues
4. **GitHub Discussions**: https://github.com/loofitheboss/loofi-fedora-tweaks/discussions

---

## License

### What license is Loofi Fedora Tweaks under?

**MIT License** — Open source, permissive license.

You are free to:
- Use the software for any purpose
- Modify the source code
- Distribute copies
- Distribute modified versions

**Requirements:**
- Include the original MIT License and copyright notice in copies

**Full license**: https://github.com/loofitheboss/loofi-fedora-tweaks/blob/master/LICENSE

---

## Project

### Who maintains this project?

Loofi Fedora Tweaks is maintained by the Loofi Team and open-source contributors.

**Lead maintainer**: [@loofitheboss](https://github.com/loofitheboss)

**Contributors**: See [Contributors](https://github.com/loofitheboss/loofi-fedora-tweaks/graphs/contributors)

### How can I contribute?

**Ways to contribute:**
- Report bugs and request features (GitHub Issues)
- Submit pull requests (code, docs, tests)
- Create plugins (Plugin SDK)
- Improve documentation (this wiki!)
- Test on different configurations (Fedora versions, desktop environments)

See: [Contributing](Contributing)

---

## Version & Updates

### What version am I running?

```bash
loofi-fedora-tweaks --cli info
```

Output includes version number and codename.

### How do I update to the latest version?

**If installed via RPM:**

```bash
# Traditional Fedora
pkexec dnf upgrade loofi-fedora-tweaks

# Atomic Fedora
rpm-ostree upgrade
systemctl reboot
```

**If running from source:**

```bash
cd loofi-fedora-tweaks/
git pull origin master
```

### What's the release schedule?

**No fixed schedule.** Releases happen when:
- Significant features are ready
- Security fixes are needed
- Bug fixes accumulate

**Versioning**: Semantic Versioning (v`MAJOR.MINOR.PATCH`)
- **Major** (v42.0.0 → v43.0.0): Breaking changes, major features
- **Minor** (v43.0.0 → v43.1.0): New features, backwards compatible
- **Patch** (v43.0.0 → v43.0.1): Bug fixes only

See: [Changelog](Changelog) for version history

---

## Still Have Questions?

- Browse other wiki pages for detailed guides
- Search [GitHub Issues](https://github.com/loofitheboss/loofi-fedora-tweaks/issues)
- Ask in [GitHub Discussions](https://github.com/loofitheboss/loofi-fedora-tweaks/discussions)
