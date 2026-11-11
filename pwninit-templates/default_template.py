#!/usr/bin/env python3
from pwn import *
from libs.debug import *

{bindings}
context.binary = {bin_name}
context.log_level = 'debug' if args.DEBUG else 'info'

p = orb_process(
    {bin_name},
    gdb_enabled=bool(args.GDB),
    files=[libc.path] if 'libc' in globals() else [],
    loader=ld.path if 'ld' in globals() else None,
)
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

pop()
