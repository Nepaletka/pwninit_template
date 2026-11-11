"""Local debug(p), or OpenSSH + QEMU for Linux x86 binaries on Apple Silicon."""

import atexit
import posixpath
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from pwn import ELF, PIPE, process, util

__all__ = ["debug", "orb_process"]


class orb_process(process):
    """A pwntools tube for one QEMU process in an SSH host (default: orb).

    gdb_enabled=True pauses QEMU at startup until debug(p) attaches.
    files are uploaded beside the executable, using their basenames.
    The default GDB port is 1234; change it for concurrent sessions.
    """

    def __init__(self, binary, argv=(), *, host="orb", gdb_enabled=True,
                 port=1234, files=(), loader=None, env=None):
        self.local_binary = str(Path(getattr(binary, "path", binary)).resolve())
        elf = ELF(self.local_binary, checksec=False)
        emulator = {"amd64": "qemu-x86_64", "i386": "qemu-i386"}.get(elf.arch)
        if emulator is None:
            raise ValueError("orb_process supports Linux amd64/i386 ELF binaries")
        self.host, self.gdb_enabled, self.port = host, gdb_enabled, int(port)
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        self.remote_dir = None
        self._closed_orb = False
        self._process_started = False
        self._temp = tempfile.TemporaryDirectory(prefix="pwn-orb-", dir="/tmp")
        self._control = str(Path(self._temp.name) / "ssh.sock")
        self._master_started = False
        try:
            qemu = self._ssh_output(
                f"command -v {emulator} || command -v {emulator}-static || "
                "{ echo 'Install qemu-user inside orb first' >&2; exit 1; }")
            self.remote_dir = self._ssh_output("mktemp -d /tmp/pwn-orb.XXXXXXXX")
            # The cleanup path must be exactly a session directory from mktemp.
            if not re.fullmatch(r"/tmp/pwn-orb\.[A-Za-z0-9]+", self.remote_dir):
                self.remote_dir = None
                raise RuntimeError("Unexpected remote mktemp output")

            uploads = {}
            for name in [self.local_binary, *files, *([loader] if loader else [])]:
                # Keep the requested basename: libc.so.6 and loaders may be
                # symlinks to versioned files. scp follows the symlink contents.
                path = Path(name).absolute()
                if not path.is_file():
                    raise ValueError(f"Not a regular file: {path}")
                if path.name in uploads and uploads[path.name] != path:
                    raise ValueError(f"Conflicting upload basenames: {path.name}")
                uploads[path.name] = path
            subprocess.run(["scp", *map(str, uploads.values()),
                            f"{host}:{self.remote_dir}/"], check=True)
            executable = "./" + Path(self.local_binary).name
            target = [executable, *map(str, argv)]
            chmod_files = [executable]
            qemu_options = []
            guest_env = dict(env or {})
            if loader:
                loader_path = "./" + Path(loader).name
                chmod_files.append(loader_path)
                interpreter = elf.linker
                if isinstance(interpreter, bytes):
                    interpreter = interpreter.decode()
                if not interpreter or not interpreter.startswith("/"):
                    raise ValueError("loader requires an ELF with an absolute PT_INTERP")
                # Keep QEMU's executable as the challenge (not ld.so), so its
                # auxv and GDB PIE relocation describe the challenge correctly.
                sysroot = self.remote_dir + "/sysroot"
                destination = sysroot + posixpath.normpath(interpreter)
                self._ssh_output(
                    "mkdir -p " + shlex.quote(str(Path(destination).parent)) +
                    " && cp " + shlex.quote(self.remote_dir + "/" + Path(loader).name) +
                    " " + shlex.quote(destination)
                )
                qemu_options += ["-L", sysroot]
                guest_env.setdefault("LD_LIBRARY_PATH", ".")
            self._ssh_output("cd " + shlex.quote(self.remote_dir) +
                             " && chmod u+x " + shlex.join(chmod_files))

            if gdb_enabled:
                subprocess.run([
                    "ssh", "-M", "-S", self._control, "-fNT",
                    "-o", "ControlPersist=no", "-o", "ExitOnForwardFailure=yes",
                    "-L", f"127.0.0.1:{self.port}:127.0.0.1:{self.port}", host,
                ], check=True)
                self._master_started = True
            command = [qemu, *qemu_options]
            for key, value in guest_env.items():
                command += ["-E", f"{key}={value}"]
            if gdb_enabled:
                command += ["-g", str(self.port)]
            command += target
            # exec preserves the PID; cleanup verifies its cwd before killing it.
            remote_command = ("cd " + shlex.quote(self.remote_dir) +
                              " && echo $$ > .qemu.pid && exec " + shlex.join(command))
            ssh_args = ["ssh", "-T", "-o", "EscapeChar=none"]
            if self._master_started:
                ssh_args += ["-S", self._control]
            # No -n and no PTY: stdin remains a binary-safe pwntools pipe.
            super().__init__([*ssh_args, host, remote_command],
                             stdin=PIPE, stdout=PIPE, stderr=None)
            self._process_started = True
            atexit.register(self.close)
        except BaseException:
            self.close()
            raise

    def _ssh_output(self, command):
        return subprocess.check_output(["ssh", self.host, command], text=True).strip()

    def close(self):
        if self._closed_orb:
            return
        self._closed_orb = True
        atexit.unregister(self.close)
        try:
            if self.remote_dir:
                # Only kill the recorded PID if it still belongs to this session.
                cleanup = (
                    f"cd {shlex.quote(self.remote_dir)} || exit 0; "
                    "if test -f .qemu.pid; then "
                    "read -r pid < .qemu.pid; "
                    "case $pid in ''|*[!0-9]*) ;; *) "
                    'if test "$(readlink /proc/$pid/cwd)" = "$PWD"; then '
                    'kill -KILL "$pid" 2>/dev/null || :; fi ;; esac; fi; '
                    f"rm -rf -- {shlex.quote(self.remote_dir)}"
                )
                try:
                    subprocess.run(["ssh", "-o", "BatchMode=yes", "-o",
                                    "ConnectTimeout=3", self.host, cleanup],
                                   timeout=5, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                except (OSError, subprocess.TimeoutExpired):
                    pass
        finally:
            if self._process_started:
                super().close()
            if self._master_started:
                try:
                    subprocess.run(["ssh", "-S", self._control, "-O", "exit", self.host],
                                   timeout=3, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            self._temp.cleanup()


def debug(p, gdbscript="continue"):
    """Attach local pwndbg to an orb QEMU stub; retain old local PID behavior."""
    if isinstance(p, orb_process):
        if not p.gdb_enabled:
            raise ValueError("Start with gdb_enabled=True before calling debug(p)")
        debugger = shutil.which("pwndbg")
        if not debugger:
            raise RuntimeError("Install local pwndbg: brew install pwndbg/tap/pwndbg-gdb")
        script = Path(p._temp.name) / "session.gdb"
        script.write_text(
            "set sysroot target:\n"
            "set tcp auto-retry on\n"
            "set tcp connect-timeout 15\n"
            f"target remote 127.0.0.1:{p.port}\n" + gdbscript + "\n"
        )
        # Older pwntools versions lack context.gdb_binary. Use the public terminal
        # launcher directly so the chosen debugger is always local pwndbg.
        return util.misc.run_in_new_terminal(
            [debugger, "-q", p.local_binary, "-x", str(script)]
        )
    pid = util.proc.pidof(p)[0]
    print(pid)
    util.proc.wait_for_debugger(pid)
