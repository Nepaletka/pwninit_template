from pwn import *
import os

def debug(p):
	pid = util.proc.pidof(p)[0]
	print(pid)
	util.proc.wait_for_debugger(pid)

def hi(p):
	os.system("python3 ~/Tools/heapinspect/HeapInspect.py %d", p.pid)


context.binary = binary = ELF('{bin_name}_patched', checksec=False)
context.log_level = "debug"

p = process()
#p = remote("host", port)



p.interactive()