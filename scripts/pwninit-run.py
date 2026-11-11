#!/usr/bin/env python3
"""Select a template and run upstream pwninit in the current task directory."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--heap", action="store_true")
    parser.add_argument("binary", type=Path)
    args, extra = parser.parse_known_args()
    if not args.binary.is_file():
        parser.error(f"binary not found: {args.binary}")
    settings = json.loads(Path(__file__).with_name("pwninit.json").read_text())
    config = Path(settings["config_dir"])
    engine = settings["engine"]
    if not shutil.which(engine):
        parser.error("pwninit is not installed; run install-macos.sh or install upstream pwninit")
    template = "heap_template.py" if args.heap else "default_template.py"
    command = [engine, "--bin", str(args.binary), "--template-path",
               str(config / "pwninit-templates" / template),
               "--template-bin-name", "exe", *extra]
    result = subprocess.run(command)
    if result.returncode:
        return result.returncode
    destination = Path.cwd() / "libs"
    destination.mkdir(exist_ok=True)
    for file in (config / "pwninit-libs").glob("*.py"):
        if file.name != "heap.py" or args.heap:
            shutil.copy2(file, destination / file.name)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
