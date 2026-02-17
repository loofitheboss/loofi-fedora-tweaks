# Codex Prompt — Serious Clean Icon Pack

```text
You are designing a production icon set for a Linux system management app (Loofi Fedora Tweaks, PyQt6 desktop app).

GOAL
Replace emoji-based UI icons with a serious, clean, professional icon pack that works on all systems without emoji fonts.

STYLE (STRICT)
- Tone: professional, technical, minimal, trustworthy
- Visual style: flat + clean line icons, consistent geometry, no playful style
- NO space/sci-fi themes, NO neon, NO cartoon style, NO gradients
- Must look good in both light and dark UI
- Legible at 16px, 20px, 24px
- Consistent stroke weight and corner radius across all icons

DELIVERABLES
1) Create exactly 24 icons.
2) Output format:
   - SVG source for each icon
   - PNG exports at 16, 20, 24, 32 px
3) Folder structure:
   - assets/icons/svg/
   - assets/icons/png/16/
   - assets/icons/png/20/
   - assets/icons/png/24/
   - assets/icons/png/32/
4) Provide:
   - assets/icons/icon-map.json (semantic_name -> file path)
   - assets/icons/README.md with usage notes and style rules
5) Keep naming lowercase kebab-case.

ICON LIST (EXACTLY 24)
Category/navigation icons (8):
1. overview-dashboard
2. packages-software
3. hardware-performance
4. network-connectivity
5. security-shield
6. appearance-theme
7. developer-tools
8. maintenance-health

Dashboard/status icons (6):
9. cpu-performance
10. memory-ram
11. network-traffic
12. storage-disk
13. status-ok
14. terminal-console

Global UI icons (5):
15. home
16. notifications
17. search
18. settings
19. info

Action icons (5):
20. install
21. update
22. cleanup
23. restart
24. logs

TECHNICAL QUALITY BAR
- Pixel-perfect alignment on 24x24 grid
- Clean path construction (no unnecessary points)
- Consistent optical weight
- Works as monochrome icons
- Avoid tiny details that disappear below 20px

OUTPUT EXPECTATION
- Generate all files and paths listed above.
- Include a quick “replacement mapping” section in README for replacing emoji contexts:
  home, bell/notifications, sidebar categories, dashboard metric cards, install/update/cleanup actions.
- If any icon concept is ambiguous, choose the most standard enterprise/system-admin visual metaphor.
```
