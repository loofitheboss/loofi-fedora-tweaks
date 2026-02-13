"""Tests for packaging scripts used in v30.0."""

import os
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASH = "/bin/bash"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _base_env(tmp_path: Path) -> dict:
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path / 'bin'}:{env.get('PATH', '')}"
    return env


def test_build_flatpak_missing_dependency(tmp_path):
    env = _base_env(tmp_path)
    (tmp_path / "bin").mkdir(parents=True, exist_ok=True)

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
    assert (ROOT / "dist" / "flatpak").exists()


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
    assert (result.stderr + result.stdout).strip()


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
    assert (ROOT / "dist" / "appimage").exists()


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
    assert "Python module 'build' is required" in (result.stderr + result.stdout)


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
        "  touch dist/loofi_fedora_tweaks-29.0.0.tar.gz\n"
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
    assert (ROOT / "dist" / "loofi_fedora_tweaks-29.0.0.tar.gz").exists()
