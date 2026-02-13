"""Tests for packaging scripts used in v30.0."""

import os
import re
import stat
import subprocess
from pathlib import Path
from shutil import copy2

ROOT = Path(__file__).resolve().parents[1]
BASH = "/bin/bash"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _base_env(tmp_path: Path) -> dict:
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path / 'bin'}:{env.get('PATH', '')}"
    return env


def _extract_version(version_file: Path) -> str:
    content = version_file.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', content, re.MULTILINE)
    assert match, "Version parse failed in test fixture"
    return match.group(1)


def test_build_flatpak_missing_dependency(tmp_path):
    env = _base_env(tmp_path)
    (tmp_path / "bin").mkdir(parents=True, exist_ok=True)

    # Restrict PATH to only contain the tmp bin dir so real flatpak-builder
    # is not found.  Keep basic system utilities available via coreutils stubs.
    env["PATH"] = str(tmp_path / "bin")

    result = subprocess.run(
        [BASH, "scripts/build_flatpak.sh"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    output = result.stderr + result.stdout
    assert output.strip()


def test_build_flatpak_success_with_stub_tools(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    _write_executable(
        bin_dir / "flatpak-builder",
        "#!/bin/bash\n"
        "repo=''\n"
        "for arg in \"$@\"; do\n"
        "  case $arg in\n"
        "    --repo=*) repo=\"${arg#--repo=}\" ;;\n"
        "  esac\n"
        "done\n"
        "mkdir -p \"$repo\"\n"
        "exit 0\n",
    )
    _write_executable(
        bin_dir / "flatpak",
        "#!/bin/bash\n"
        "if [[ \"$1\" == \"build-bundle\" ]]; then\n"
        "  touch \"$3\"\n"
        "fi\n"
        "exit 0\n",
    )
    _write_executable(bin_dir / "tar", "#!/bin/bash\nexit 0\n")

    env = _base_env(tmp_path)
    result = subprocess.run(
        [BASH, "scripts/build_flatpak.sh"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    version = _extract_version(ROOT / "loofi-fedora-tweaks" / "version.py")
    expected_bundle = ROOT / "dist" / "flatpak" / \
        f"loofi-fedora-tweaks-v{version}.flatpak"
    assert expected_bundle.exists()


def test_build_flatpak_missing_manifest(tmp_path):
    project_root = tmp_path / "project"
    (project_root / "scripts").mkdir(parents=True, exist_ok=True)
    (project_root / "loofi-fedora-tweaks").mkdir(parents=True, exist_ok=True)

    copy2(ROOT / "scripts" / "build_flatpak.sh",
          project_root / "scripts" / "build_flatpak.sh")
    (project_root / "loofi-fedora-tweaks" / "version.py").write_text(
        '__version__ = "30.0.0"\n',
        encoding="utf-8",
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    _write_executable(bin_dir / "flatpak-builder", "#!/bin/bash\nexit 0\n")
    _write_executable(bin_dir / "flatpak", "#!/bin/bash\nexit 0\n")
    _write_executable(bin_dir / "tar", "#!/bin/bash\nexit 0\n")

    env = _base_env(tmp_path)
    result = subprocess.run(
        [BASH, "scripts/build_flatpak.sh"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Flatpak manifest not found" in (result.stderr + result.stdout)


def test_build_flatpak_version_parse_failure(tmp_path):
    project_root = tmp_path / "project"
    (project_root / "scripts").mkdir(parents=True, exist_ok=True)
    (project_root / "loofi-fedora-tweaks").mkdir(parents=True, exist_ok=True)

    copy2(ROOT / "scripts" / "build_flatpak.sh",
          project_root / "scripts" / "build_flatpak.sh")
    (project_root / "loofi-fedora-tweaks" / "version.py").write_text(
        '__version_codename__ = "Distribution & Reliability"\n',
        encoding="utf-8",
    )
    (project_root / "org.loofi.FedoraTweaks.yml").write_text(
        "app-id: org.loofi.FedoraTweaks\n", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    _write_executable(bin_dir / "flatpak-builder", "#!/bin/bash\nexit 0\n")
    _write_executable(bin_dir / "flatpak", "#!/bin/bash\nexit 0\n")
    _write_executable(bin_dir / "tar", "#!/bin/bash\nexit 0\n")

    env = _base_env(tmp_path)
    result = subprocess.run(
        [BASH, "scripts/build_flatpak.sh"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Failed to parse version" in (result.stderr + result.stdout)


def test_build_appimage_missing_dependency(tmp_path):
    env = _base_env(tmp_path)
    (tmp_path / "bin").mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [BASH, "scripts/build_appimage.sh"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Missing required tool" in (result.stderr + result.stdout)


def test_build_appimage_success_with_stub_tools(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    _write_executable(
        bin_dir / "linuxdeploy",
        "#!/bin/bash\n"
        "if [[ \"$1\" == \"--version\" ]]; then\n"
        "  echo linuxdeploy\n"
        "fi\n"
        "exit 0\n",
    )
    _write_executable(
        bin_dir / "appimagetool",
        "#!/bin/bash\n"
        "touch \"$2\"\n"
        "exit 0\n",
    )

    env = _base_env(tmp_path)
    result = subprocess.run(
        [BASH, "scripts/build_appimage.sh"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    version = _extract_version(ROOT / "loofi-fedora-tweaks" / "version.py")
    expected_appimage = ROOT / "dist" / "appimage" / \
        f"loofi-fedora-tweaks-v{version}-x86_64.AppImage"
    assert expected_appimage.exists()


def test_build_appimage_linuxdeploy_from_env_var(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    custom_linuxdeploy = tmp_path / "linuxdeploy-custom"
    _write_executable(custom_linuxdeploy, "#!/bin/bash\nexit 0\n")
    _write_executable(bin_dir / "appimagetool",
                      "#!/bin/bash\ntouch \"$2\"\nexit 0\n")

    env = _base_env(tmp_path)
    env["LINUXDEPLOY_BIN"] = str(custom_linuxdeploy)
    result = subprocess.run(
        [BASH, "scripts/build_appimage.sh"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0


def test_build_appimage_missing_desktop_file(tmp_path):
    project_root = tmp_path / "project"
    (project_root / "scripts").mkdir(parents=True, exist_ok=True)
    (project_root / "loofi-fedora-tweaks" /
     "assets").mkdir(parents=True, exist_ok=True)

    copy2(ROOT / "scripts" / "build_appimage.sh",
          project_root / "scripts" / "build_appimage.sh")
    (project_root / "loofi-fedora-tweaks" /
     "version.py").write_text('__version__ = "30.0.0"\n', encoding="utf-8")
    (project_root / "loofi-fedora-tweaks" /
     "main.py").write_text("print('ok')\n", encoding="utf-8")
    (project_root / "loofi-fedora-tweaks" /
     "assets" / "icon.png").write_bytes(b"png")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    _write_executable(bin_dir / "linuxdeploy", "#!/bin/bash\nexit 0\n")
    _write_executable(bin_dir / "appimagetool", "#!/bin/bash\nexit 0\n")

    env = _base_env(tmp_path)
    result = subprocess.run(
        [BASH, "scripts/build_appimage.sh"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Missing desktop file" in (result.stderr + result.stdout)


def test_build_sdist_missing_build_module(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    _write_executable(
        bin_dir / "python3",
        "#!/bin/bash\n"
        "if [[ \"$1\" == \"-c\" ]]; then\n"
        "  exit 1\n"
        "fi\n"
        "exit 0\n",
    )

    env = _base_env(tmp_path)
    result = subprocess.run(
        [BASH, "scripts/build_sdist.sh"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Python module 'build' is required" in (
        result.stderr + result.stdout)


def test_build_sdist_success_with_stub_python(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    _write_executable(
        bin_dir / "python3",
        "#!/bin/bash\n"
        "if [[ \"$1\" == \"-c\" ]]; then\n"
        "  exit 0\n"
        "fi\n"
        "if [[ \"$1\" == \"-m\" && \"$2\" == \"build\" ]]; then\n"
        "  mkdir -p dist\n"
        f"  touch dist/loofi_fedora_tweaks-{_extract_version(ROOT / 'loofi-fedora-tweaks' / 'version.py')}.tar.gz\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
    )

    env = _base_env(tmp_path)
    result = subprocess.run(
        [BASH, "scripts/build_sdist.sh"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    version = _extract_version(ROOT / "loofi-fedora-tweaks" / "version.py")
    assert (ROOT / "dist" / f"loofi_fedora_tweaks-{version}.tar.gz").exists()
