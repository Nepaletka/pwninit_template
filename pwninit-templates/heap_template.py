#!/usr/bin/env python3

from pwn import *
from libs.debug import *
from libs.heap import *

#https://agrohacksstuff.io/posts/pwntools-tricks-and-examples/

context.binary = binary = ELF('{bin_name}_patched', checksec=False)
context.terminal = ['gnome-terminal', '--']
context.log_level = "debug"

sl = lambda x: p.sendline(x)
sa = lambda x, y: p.sendafter(x, y)
sla = lambda x, y: p.sendlineafter(x, y)
ru = lambda x: p.recvuntil(x)

p = process()
#p = remote("host", port)

p.interactive()