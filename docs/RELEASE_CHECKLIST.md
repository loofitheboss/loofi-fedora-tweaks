# Release Checklist

Use this checklist before tagging a release.

## v28.0.0 Kickoff Notes

- Workflow state reset to v28.0.0 baseline (planning artifacts, race lock, run manifest).
- Task contract validation enforced via workflow_runner.py markers and continuation fields.
- Planning checkpoint recorded in run manifest for phase progression tracking.

---

## 1. Version Alignment

Update and verify version fields stay in sync:

1. `loofi-fedora-tweaks/version.py` - `__version__`, `__version_codename__`
2. `loofi-fedora-tweaks.spec` - `Version:`

Quick verify:

```bash
rg -n "__version__|__version_codename__" loofi-fedora-tweaks/version.py
rg -n "^Version:" loofi-fedora-tweaks.spec
```

---

## 2. Documentation

1. Update `CHANGELOG.md`
2. Add/update `docs/releases/RELEASE-NOTES-vX.Y.Z.md`
3. Update `README.md` for current release and command examples
4. Update `docs/USER_GUIDE.md` for new behavior/features
5. Update `docs/TROUBLESHOOTING.md` for new failure modes
6. Update `docs/CONTRIBUTING.md` if workflows changed

---

## 3. Tests and Lint

Run full tests:

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --cov-fail-under=80
```

Run lint:

```bash
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722
```

---

## 4. Package Build

Build RPM:

```bash
bash scripts/build_rpm.sh
```

Verify output exists:

```bash
ls -lah rpmbuild/RPMS/noarch/
```

---

## 5. Smoke Test

Use installed binary or source run target and verify key commands:

```bash
loofi-fedora-tweaks --version
loofi-fedora-tweaks --cli info
loofi-fedora-tweaks --cli doctor
loofi-fedora-tweaks --cli plugins list
loofi-fedora-tweaks --cli plugin-marketplace search --query test
```

Optional GUI smoke test:

```bash
loofi-fedora-tweaks
```

---

## 6. Commit and Tag

Commit release changes:

```bash
git add -A
git commit -m "Release vX.Y.Z Codename"
```

Create tag:

```bash
git tag -a vX.Y.Z -m "vX.Y.Z Codename"
```

Push branch and tags:

```bash
git push origin master
git push origin vX.Y.Z
```

---

## 7. GitHub Release Validation

After CI/workflows complete:

```bash
gh release list --limit 3
gh release view vX.Y.Z
```

Confirm:

1. Tag exists and points to intended commit.
2. Release notes are correct.
3. RPM artifacts are attached.
4. `ROADMAP.md` release status is updated if applicable.
