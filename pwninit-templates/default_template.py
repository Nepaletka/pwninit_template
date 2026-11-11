#!/usr/bin/env python3
from pwn import *
from libs.debug import *

context.binary = exe = ELF('{bin_name}_patched', checksec=False)
context.terminal = ['tmux', 'splitw', '-h']
context.log_level = 'debug'

# SSH uses the existing `ssh orb` configuration. No gdbserver is involved.
p = orb_process(exe, gdb_enabled=bool(args.GDB))
# For a supplied libc/loader, use instead:
# p = orb_process(exe, gdb_enabled=bool(args.GDB),
#                 files=['libc.so.6'], loader='ld-linux-x86-64.so.2')
if args.GDB:
    debug(p, 'break main\ncontinue')

se   = lambda data  : p.send(data)
sl   = lambda data  : p.sendline(data)
sa   = lambda ip,op : p.sendafter(ip,op)
sla  = lambda ip,op : p.sendlineafter(ip,op)
ru   = lambda data  : p.recvuntil(data)
rl   = lambda      : p.recvline()
rv   = lambda n    : p.recv(n)
pop  = lambda      : p.interactive()
log  = lambda nm,v : p.info(nm.upper() + ' : ' + hex(v))
leak = lambda n    : u64(p.recv(n).ljust(8, b'\x00'))

# EXPLOIT STARTS HERE

pop()
