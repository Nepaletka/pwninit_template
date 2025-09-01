#!/usr/bin/env python3
from pwn import *
from libs.debug import *
from libs.heap import *

#https://agrohacksstuff.io/posts/pwntools-tricks-and-examples/

# ==================[START DEFINIITONS]======================
context.binary = exe = ELF('{bin_name}_patched', checksec=False)
context.terminal = ['gnome-terminal', '--']
context.log_level = "debug"

p = process()
#p = remote("host", port)

# =======================[EXPANSIONS]============================
se   = lambda data  : p.send(data)
sl   = lambda data  : p.sendline(data)
sa   = lambda ip,op : p.sendafter(ip,op)
sla  = lambda ip,op : p.sendlineafter(ip,op) 
ru  = lambda data  : p.recvuntil(data)
rl  = lambda       : p.recvline()
rv   = lambda nbyts : p.recv(nbyts)  
pop  = lambda       : p.interactive()
log  = lambda nm,v  : p.info(f"{nm.upper()} : {hex(v)}")
leak = lambda num   : u64(p.recv(num).ljust(8,b"\x00"))

# >>>>>>>>>>>>>>>>>>>[EXPLOIT STARTS HERE]>>>>>>>>>>>>>>>>>>>>>>>


pop()