from pwn import util

def debug(p):
	pid = util.proc.pidof(p)[0]
	print(pid)
	util.proc.wait_for_debugger(pid)

