# Loofi Fedora Tweaks v25.0.1 "Plugin Architecture Hotfix"

## Highlights

- Fix plugin startup regression by removing `ABC` metaclass coupling from `PluginInterface`.
- Fix `BaseTab` compatibility by removing `pyqtWrapperType` dependency.
- Reduce noisy startup logs in restricted DBus environments by downgrading expected failures.

## Installation

```bash
sudo dnf install ./loofi-fedora-tweaks-25.0.1-1.noarch.rpm
```

## Full Changelog

See `CHANGELOG.md` for the complete list of changes.
