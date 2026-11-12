#!/usr/bin/env python3
from pwn import *
from libs.debug import *

#https://agrohacksstuff.io/posts/pwntools-tricks-and-examples/

# ==================[START DEFINIITONS]======================
{bindings}
context.binary = exe
context.log_level = "debug"

p = orb_process(
    exe,
    gdb_enabled=bool(args.GDB),
    files=[libc.path] if 'libc' in globals() else [],
    loader=ld.path if 'ld' in globals() else None,
)
if args.GDB:
    debug(p, 'break main\ncontinue')

# =======================[EXPANSIONS]============================
se   = lambda data  : p.send(data)
sl   = lambda data  : p.sendline(data)
sa   = lambda ip,op : p.sendafter(ip,op)
sla  = lambda ip,op : p.sendlineafter(ip,op)
ru  = lambda data  : p.recvuntil(data)
rl  = lambda       : p.recvline()
rv   = lambda nbyts : p.recv(nbyts)
pop  = lambda       : p.interactive()
log  = lambda nm,v  : p.info(nm.upper() + " : " + hex(v))
leak = lambda num   : u64(p.recv(num).ljust(8,b"\x00"))

# >>>>>>>>>>>>>>>>>>>[EXPLOIT STARTS HERE]>>>>>>>>>>>>>>>>>>>>>>>

pop()

