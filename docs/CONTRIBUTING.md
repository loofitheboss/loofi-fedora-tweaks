# Contributing to Loofi Fedora Tweaks

Thank you for considering contributing! Here's how you can help.

## 🐛 Reporting Bugs

1. Search [existing issues](https://github.com/loofitheboss/loofi-fedora-tweaks/issues) to avoid duplicates.
2. Open a new issue with:
    * **Title**: Short and descriptive.
    * **Steps to Reproduce**: What did you do?
    * **Expected Behavior**: What should have happened?
    * **Actual Behavior**: What happened instead?
    * **Environment**: Fedora version, KDE Plasma version, Python version.

## 💡 Feature Requests

Open an issue with the **enhancement** label. Describe:

* The problem you're trying to solve.
* Your proposed solution.

## 🛠️ Pull Requests

1. **Fork** the repository.
2. **Create a branch**: `git checkout -b feature/your-feature-name`
3. **Make changes** and commit: `git commit -m "Add your feature"`
4. **Push**: `git push origin feature/your-feature-name`
5. **Open a Pull Request** on GitHub.

### Code Style

* Python: Follow PEP 8.
* Use meaningful variable names.
* Comment complex logic.

## 📁 Project Structure

```
loofi-fedora-tweaks/
├── loofi-fedora-tweaks/       # Main application source
│   ├── main.py               # Entry point
│   ├── ui/                   # PyQt6 UI components
│   │   ├── main_window.py    # Main window with sidebar
│   │   ├── dashboard_tab.py  # Dashboard (Home) screen
│   │   ├── updates_tab.py    # System updates
│   │   ├── cleanup_tab.py    # System cleanup
│   │   ├── tweaks_tab.py     # HP Elitebook tweaks
│   │   ├── gaming_tab.py     # Gaming optimizations
│   │   ├── network_tab.py    # Network & privacy
│   │   └── ...               # Other tabs
│   ├── utils/                # Utility modules
│   │   ├── process.py        # Command execution
│   │   ├── safety.py         # Snapshot & lock handling
│   │   ├── history.py        # Undo system
│   │   └── ...
│   ├── assets/               # Icons, QSS themes
│   │   ├── modern.qss        # Dark theme
│   │   └── loofi-fedora-tweaks.png
│   └── config/               # Default configs
├── docs/                     # Documentation
│   ├── USER_GUIDE.md         # User guide
│   └── CONTRIBUTING.md       # This file
├── tests/                    # Unit tests
├── repo/                     # Built RPMs
├── build_rpm.sh              # Build script
├── loofi-fedora-tweaks.spec  # RPM spec file
├── requirements.txt          # Python dependencies
└── README.md                 # Project overview
```

## 🧪 Running Tests

```bash
cd loofi-fedora-tweaks
PYTHONPATH=./loofi-fedora-tweaks python3 -m pytest tests/
```

## 📦 Building the RPM

```bash
./build_rpm.sh
```

The RPM will be output to `rpmbuild/RPMS/noarch/`.

---

Thanks for contributing! 🙏
