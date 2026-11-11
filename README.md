# pwninit_template
## Setup

1. Clone the repo
```
git clone https://github.com/Nepaletka/pwninit_template
cd pwninit_template
```
2. Run script
```
./setup.sh
```
3. Reload your shell configuration
```
source ~/.zshrc
```

## macOS / OrbStack debugging

The templates can run Linux x86 binaries in the `orb` SSH host with QEMU and
open local pwndbg through `debug(p)`. Existing pwntools I/O helpers still work.

See [OrbStack setup and usage](docs/orb-debugging.md) for dependencies, launching
with `GDB`, supplied libc/loader support, and cleanup behavior.
