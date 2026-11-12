#!/usr/bin/env python3
"""Compile a C/C++ source in the SSH VM and download its Linux ELF."""

import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile


def compile_source(source, output=None, *, host="orb", cc="gcc", flags=()):
    source = Path(source).expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError(f"not a regular file: {source}")
    output = Path(output or source.stem).expanduser().absolute()
    if output.resolve() == source:
        raise ValueError("output must not overwrite the source")
    if output.is_dir():
        raise ValueError(f"output is a directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    remote = subprocess.check_output(
        ["ssh", host, "mktemp -d /tmp/pwncompile.XXXXXXXX"], text=True).strip()
    if not re.fullmatch(r"/tmp/pwncompile\.[A-Za-z0-9]+", remote):
        raise RuntimeError("unexpected remote mktemp output")
    try:
        # SSH stdin avoids remote scp quoting differences for source filenames.
        with source.open("rb") as contents:
            subprocess.run(["ssh", host, "cat > " + shlex.quote(remote + "/" + source.name)],
                           stdin=contents, check=True)
        command = [cc, "-m64", "-g3", "-O0", "-fno-omit-frame-pointer",
                   f"-fdebug-prefix-map={remote}={source.parent}", *flags,
                   "./" + source.name, "-o", "program"]
        subprocess.run(["ssh", host, "cd " + shlex.quote(remote) +
                        " && " + shlex.join(command)], check=True)
        with tempfile.TemporaryDirectory(prefix=".pwncompile-", dir=output.parent) as folder:
            downloaded = Path(folder) / "program"
            subprocess.run(["scp", f"{host}:{remote}/program", str(downloaded)], check=True)
            with downloaded.open("rb") as binary:
                if binary.read(4) != b"\x7fELF":
                    raise RuntimeError("compiler output is not a Linux ELF")
            downloaded.chmod(downloaded.stat().st_mode | 0o100)
            os.replace(downloaded, output)
    finally:
        try:
            subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", host,
                            "rm -rf -- " + shlex.quote(remote)],
                           timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return output


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    flags = []
    if "--" in argv:
        separator = argv.index("--")
        argv, flags = argv[:separator], argv[separator + 1:]
    parser = argparse.ArgumentParser(description=__doc__,
        epilog="Example: pwncompile test.c -o chall -- -fno-stack-protector -no-pie")
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", type=Path, help="default: source filename without extension")
    parser.add_argument("--host", default="orb", help="SSH alias (default: orb)")
    parser.add_argument("--cc", default="gcc", help="compiler in the VM (e.g. gcc or g++)")
    args = parser.parse_args(argv)
    output = compile_source(args.source, args.output, host=args.host, cc=args.cc, flags=flags)
    print(f"Built {output}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
    except (OSError, ValueError, RuntimeError) as error:
        sys.exit(str(error))
