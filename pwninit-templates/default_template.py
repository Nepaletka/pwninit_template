from pwn import *
from libs.debug import *

context.binary = binary = ELF('{bin_name}_patched', checksec=False)
context.log_level = "debug"

p = process()
#p = remote("host", port)

p.interactive()