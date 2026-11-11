#!/usr/bin/env python3
"""Install the templates, zsh commands, and optional macOS dependencies."""

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
START = "# >>> pwninit_template >>>"
END = "# <<< pwninit_template <<<"


def install_dependencies(config_dir):
    if platform.system() != "Darwin":
        raise RuntimeError("--macos requires macOS; use ./setup.sh on Linux")
    brew = shutil.which("brew")
    if not brew:
        raise RuntimeError("Install Homebrew first: https://brew.sh")
    subprocess.run([brew, "install", "python", "rust", "pkgconf", "openssl@3",
                    "xz", "patchelf", "pwndbg/tap/pwndbg-gdb"], check=True)
    if not any(p.exists() for p in [Path("/Applications/Ghostty.app"),
                                    Path.home() / "Applications/Ghostty.app"]):
        subprocess.run([brew, "install", "--cask", "ghostty"], check=True)
    prefix = subprocess.check_output([brew, "--prefix"], text=True).strip()
    python = str(Path(prefix) / "bin/python3")
    venv = config_dir / "pwninit-env"
    subprocess.run([python, "-m", "venv", str(venv)], check=True)
    python = str(venv / "bin/python")
    subprocess.run([python, "-m", "pip", "install", "pwntools>=4.14,<5"], check=True)
    engine = config_dir / "pwninit-tool/bin/pwninit"
    if not engine.exists():
        env = os.environ.copy()
        env["OPENSSL_DIR"] = subprocess.check_output(
            [brew, "--prefix", "openssl@3"], text=True).strip()
        subprocess.run([str(Path(prefix) / "bin/cargo"), "install", "--locked",
                        "--root", str(config_dir / "pwninit-tool"), "pwninit"],
                       check=True, env=env)
    return python, str(engine)


def update_zshrc(path, integration):
    original = path.read_text() if path.exists() else ""
    text = re.sub(r"(?ms)^" + re.escape(START) + r"\n.*?^" + re.escape(END) +
                  r"\n?", "", original)
    text = re.sub(r"(?ms)^pwninit\(\) \{\n.*?^\}\n?", "", text)
    block = f"{START}\nsource {shlex.quote(str(integration))}\n{END}\n"
    updated = text.rstrip("\n") + ("\n\n" if text.rstrip("\n") else "") + block
    if updated == original:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = path.with_name(path.name + ".pwninit.bak")
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(updated)


def install(config_dir, zshrc, python, engine):
    config_dir.mkdir(parents=True, exist_ok=True)
    for folder in ["pwninit-templates", "libs"]:
        destination = config_dir / ("pwninit-libs" if folder == "libs" else folder)
        destination.mkdir(exist_ok=True)
        for file in (ROOT / folder).glob("*.py"):
            shutil.copy2(file, destination / file.name)
    shutil.copy2(ROOT / "scripts/pwninit-run.py", config_dir / "pwninit-run.py")
    settings = {"config_dir": str(config_dir), "engine": engine, "python": python}
    (config_dir / "pwninit.json").write_text(json.dumps(settings, indent=2) + "\n")
    integration = config_dir / "pwninit.zsh"
    integration.write_text(
        "pwninit() {\n  " + shlex.quote(python) + " " +
        shlex.quote(str(config_dir / "pwninit-run.py")) + ' "$@"\n}\n\n' +
        "pwnpy() {\n  " + shlex.quote(python) + ' "$@"\n}\n'
    )
    update_zshrc(zshrc, integration)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--macos", action="store_true", help="install Homebrew tools and a Python venv")
    parser.add_argument("--skip-deps", action="store_true", help="only install templates and shell integration")
    parser.add_argument("--config-dir", type=Path,
                        default=Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")))
    parser.add_argument("--zshrc", type=Path, default=Path(os.environ.get("ZDOTDIR", Path.home())) / ".zshrc")
    args = parser.parse_args()
    config_dir = args.config_dir.expanduser().resolve()
    config_dir.mkdir(parents=True, exist_ok=True)
    python, engine = sys.executable, shutil.which("pwninit") or "pwninit"
    settings_file = config_dir / "pwninit.json"
    if settings_file.exists():
        existing = json.loads(settings_file.read_text())
        python, engine = existing.get("python", python), existing.get("engine", engine)
    if args.macos and not args.skip_deps:
        python, engine = install_dependencies(config_dir)
    install(config_dir, args.zshrc.expanduser().resolve(), python, engine)
    print("Installed. In your shell, run:")
    print("source " + shlex.quote(str(args.zshrc.expanduser().resolve())))
    if args.macos:
        print("In orb, install QEMU: ssh -t orb 'sudo apt install -y qemu-user'")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
