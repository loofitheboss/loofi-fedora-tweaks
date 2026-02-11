# Established Patterns

## QSS Theme Files
- Located in `loofi-fedora-tweaks/assets/`
- `modern.qss` = dark theme (Catppuccin Mocha palette)
- `light.qss` = light theme (Catppuccin Latte palette)
- `style.qss` = legacy, not loaded by default
- Object names used for scoping: `#breadcrumbBar`, `#statusBar`, `#sidebarFooter`, `#bcCategory`, `#bcSep`, `#bcPage`, `#bcDesc`, `#statusText`, `#statusHints`, `#statusVersion`, `#sidebar`, `#outputArea`

## Tab Configuration
- `configure_top_tabs(tab_widget)` in `tab_utils.py` is called by all multi-sub-tab pages
- Sets: scrollButtons=True, elideMode=ElideRight, expanding=False, documentMode=False
- 14 tabs currently call this function

## Layout Pattern
- Root layout is always zero-margin HBox
- Content tabs should use scroll areas for overflow
- Sidebar is QTreeWidget with categories (top-level) and pages (children)

## Inline Style Problem
- ~130 inline setStyleSheet calls across UI files
- Most hardcode Catppuccin Mocha colors (dark theme)
- These will NOT adapt when switching to light theme
- Long-term fix: move to object-name-based QSS selectors
