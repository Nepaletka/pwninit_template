from pwn import *

context.binary = binary = ELF('{bin_name}_patched', checksec=False)
context.log_level = "debug"

p = process()
p = remote("host", port)

#debug
pid = util.proc.pidof(p)[0]
print(pid)
util.proc.wait_for_debugger(pid)


p.interactive()