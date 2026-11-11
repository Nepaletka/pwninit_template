# Pwntools + OrbStack + local pwndbg

This adapts Nepaletka/pwninit_template, inspected at commit
`6c956433dad94d8aac72b90d18fb05c726cea890`.
It uses OpenSSH's `orb` alias, QEMU's own GDB stub, and a local pwndbg window.
There is no remote gdbserver/ptrace attach.

## Install

On the Mac, use your Python environment with pwntools installed. Install tmux
and pwndbg if needed:

```sh
brew install tmux pwndbg/tap/pwndbg-gdb
ssh -t orb 'sudo apt install -y qemu-user'
```

Copy `libs/debug.py` to the `libs/debug.py` alongside your exploit. The two
files under `pwninit-templates/` can replace the corresponding files in your
template repository. To affect future generated tasks, update the copies used
by your setup: `~/.config/pwninit-libs/debug.py` and
`~/.config/pwninit-templates/{default,heap}_template.py`.
Existing task directories have their own copies and need updating separately.

## Change an existing exploit

Keep `from libs.debug import *` and `context.binary = exe = ELF(...)`.
Replace `context.terminal` and `p = process()` with:

```python
context.terminal = ['tmux', 'splitw', '-h']
p = orb_process(exe, gdb_enabled=bool(args.GDB))
if args.GDB:
    debug(p, 'break main\ncontinue')
```

Your existing `se/sl/sa/sla/ru/rl/rv/pop` helpers still use the same `p` tube.
Run from a tmux session on the Mac:

```sh
tmux new-session -s pwn
python3 solve.py GDB
```

Without `GDB`, `python3 solve.py` runs under QEMU without a debugger.
With `GDB`, QEMU waits for debug(p). Call debug(p) before the first send/recv.
The sample stops at main; enter `continue` in pwndbg to let I/O proceed.
For stripped challenges, replace `break main` with a suitable breakpoint or
just use `debug(p)` to connect and continue.

## Supplied libc and loader (pwninit)

```python
p = orb_process(
    exe,
    gdb_enabled=bool(args.GDB),
    files=['libc.so.6'],
    loader='ld-linux-x86-64.so.2',
)
if args.GDB:
    debug(p, 'break main\ncontinue')
```

Use the actual loader filename in your task. The library must be uploaded with
the name its loader searches for, usually `libc.so.6`. For a versioned libc,
make a local `libc.so.6` copy/symlink first and pass that path.

Files are flattened to their basenames in a unique remote session directory;
basename collisions are rejected. Only explicitly listed files are uploaded.
The supplied loader is installed into a session-local QEMU interpreter prefix,
matching the executable's original PT_INTERP (including absolute paths in
`*_patched` files). The executable itself remains unchanged, which preserves
GDB's PIE relocation. `LD_LIBRARY_PATH=.` selects the supplied libraries.
Other dependencies and data files must be passed via `files` as needed.

Optional arguments: `host='orb'`, `port=1234`, `argv=[...]`, `env={...}`.
Supported targets: Linux amd64 and i386 (the latter requires qemu-i386 and the
appropriate 32-bit loader/libraries inside the VM).

## I/O and lifecycle

stdin/stdout use SSH pipes, so payloads including NUL/0xff are preserved.
Unlike a terminal, pipes don't force libc stdout to be line buffered. If a
challenge doesn't flush its prompts, recvuntil/sendlineafter may need a target
buffering fix. stderr is sent to the parent terminal, outside the payload tube.

The returned tube supports context-manager usage and p.close(). Normal Python
exit also runs cleanup: kill the recorded QEMU process if it is still in the
session directory, remove remote files, close the SSH master/tunnel, and remove
local temporary files. Forked processes, a process that changes cwd, SIGKILL,
or loss of connectivity can require manual cleanup. The OrbStack VM stays up.

Port 1234 is reserved on the Mac by the tunnel; another active listener causes
a clear SSH error. For concurrent sessions use a distinct `port` in each one.
The remote QEMU listener also needs that port free. Don't connect another GDB
to a session's port. This is for your controlled orb target; it does not grant
debug access to an arbitrary CTF service reached through remote(host, port).

## Validation

An end-to-end test in the connected orb runs a compiled amd64 PIE program with
and without GDB, checks a breakpoint in main, sends/receives five bytes including
NUL/0xff/CR/LF, checks the supplied-loader/libc mode, and checks remote session
directory cleanup. The debugger launch in the test is headless; interactive
tmux window creation is not part of that test. i386 is not tested.

References:
- https://docs.orbstack.dev/machines/#debugging-with-gdb-lldb
- https://docs.pwntools.com/en/stable/util/misc.html
- https://docs.pwntools.com/en/stable/tubes/processes.html
