#!python3

import logging
import pprint
import struct
import sys


class FixedSizeStack(bytearray):
    def __init__(self, capacity: int):
        self.capacity = capacity
        super().__init__(0)

    def push(self, b: int):
        assert len(self) < self.capacity
        super().append(b)

    def __repr__(self) -> str:
        return f"[{', '.join(hex(i) for i in self)}]"

    def __str__(self) -> str:
        return repr(self)

class Uxn:
    RESET = 0x100

    def __init__(self) -> None:
        self.pc = 0
        self.mem = bytearray(0x10_000)
        self.dev = bytearray(0x100)
        self.ws = FixedSizeStack(0x100)
        self.rs = FixedSizeStack(0x100)

def spop(s: FixedSizeStack):
    r = struct.unpack_from("@b", s, len(s) - 1)[0]
    s.pop()
    return r

def ushort_peek(ba: bytearray, offset: int) -> int:
    return struct.unpack_from(">H", ba, offset)[0]

def sshort_peek(ba: bytearray, offset: int) -> int:
    return struct.unpack_from(">h", ba, offset)[0]

def ushort_pop(s: FixedSizeStack) -> int:
    r = ushort_peek(s, len(s)-2)
    s.pop()
    s.pop()
    return r

def sshort_pop(s: FixedSizeStack) -> int:
    r = sshort_peek(s, len(s)-2)
    s.pop()
    s.pop()
    return r

# Console Device
 
CONSOLE_DEVICE = 0x10
ConsoleVectorPtr = 0x10

CONSOLE_WRITE_PORT= 0x8
ConsoleNoQueue = 0
ConsoleStdIn = 1
ConsoleArg = 2
ConsoleArgSpacer = 3
ConsoleArgEnd = 4

def console_device(port: int, value: int):
    if port == CONSOLE_WRITE_PORT:
        sys.stdout.write(chr(value))
    else:
        raise ValueError(f"Unknown console port: {port}")


# Ops
def op_imm(u: Uxn, mode2, moder, modek):
    match (mode2, moder, modek):
        case (0,0,0):
            return 1
        case (1,0,0):
            op_jci(u)
        case (0,1,0):
            op_jmi(u)
        case (1,1,0):
            op_jsi(u)
        case (mode2,moder,1): 
            op_lit(u, mode2, moder, modek)

def op_jci(u: Uxn):
    if u.ws.pop():
        u.pc += sshort_peek(u.mem, u.pc)
    u.pc += 2

def op_jmi(u: Uxn):
    u.pc += sshort_peek(u.mem,u.pc) + 2

def op_jsi(u: Uxn):
    offset_ptr = u.pc
    u.pc += 2
    u.rs.push(u.pc >> 8)
    u.rs.push(u.pc & 0xff)
    offset = (u.mem[offset_ptr] << 8) + u.mem[offset_ptr+1]
    u.pc += offset

def op_lit(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    pc = u.pc+1+mode2
    lit = u.mem[u.pc:pc]
    s.extend(lit)
    u.pc = pc


def op_inc(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    if mode2:
        x = s.pop() + (s.pop() << 8) + 1
        s.push(x >> 8)
        s.push(x & 0xff)
    else:
        s.push(x + 1)


def op_pop(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    s.pop()
    if mode2:
        s.pop()


def op_nip(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    top = s.pop()
    s.pop()
    s.push(top)


def op_swp(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    top = s.pop()
    bot = s.pop()
    s.push(top)
    s.push(bot)


def op_rot(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    top = s.pop()
    mid = s.pop()
    bot = s.pop()
    s.push(bot)
    s.push(top)
    s.push(mid)


def op_dup(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    top = s.pop()
    s.push(top)
    s.push(top)


def op_ovr(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    top = s.pop()
    bot = s.pop()
    s.push(top)
    s.push(bot)
    s.push(bot)


def op_equ(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    top = s.pop()
    bot = s.pop()
    s.push(int(bot == top))


def op_neq(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    top = s.pop()
    bot = s.pop()
    s.push(int(bot != top))


def op_gth(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    top = s.pop()
    bot = s.pop()
    s.push(int(bot > top))


def op_lth(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    top = s.pop()
    bot = s.pop()
    s.push(int(bot < top))


def op_jmp(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    if mode2:
        u.pc = s.pop() + (s.pop() << 8)
    else:
        (top,) = struct.unpack_from("@b", s, len(s) - 1)
        s.pop()
        u.pc += top


def op_jcn(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    (top,) = struct.unpack_from("@b", s, len(s) - 1)
    s.pop()
    if s.pop() != 0:
        u.pc += top


def op_jsr(u: Uxn, mode2, moder, modek):
    s1,s2 = (u.rs, u.ws) if moder else ( u.ws, u.rs)
    s2.extend((u.pc >> 8, u.pc & 255))
    u.pc = ushort_pop(s1) if mode2 else u.pc + spop(s1)


def op_sth(u: Uxn, mode2, moder, modek):
    s1,s2 = (u.rs, u.ws) if moder else ( u.ws, u.rs)
    top = s1.pop()
    if mode2:
        s2.push(s1.pop())
    s2.push(top)

def op_lda(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws 
    if modek:
        addr = s[-1] + (s[-2] << 8)
    else:
        addr = s.pop() + (s.pop() << 8)
    s.push(u.mem[addr])
    if mode2:
        s.push(u.mem[addr + 1])
    

def op_sta(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    addr = s.pop() + (s.pop() << 8)
    if mode2:
        s2.push(s1.pop())
    s2.push(top)

def op_deo(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    device_port = s.pop()
    device = device_port & 0xf0
    port = device_port & 0xf
    if device == CONSOLE_DEVICE:
        console_device(device_port & 0xf, s.pop())
    else:
        raise NotImplementedError

def op_add(u: Uxn, mode2, moder, modek):
    s = u.rs if moder else u.ws
    x = s.pop()
    y = s.pop()
    s.push(x+y)



OPS = {
    0x00: op_imm,
    0x01: op_inc,
    0x02: op_pop,
    0x03: op_nip,
    0x04: op_swp,
    0x05: op_rot,
    0x06: op_dup,
    0x07: op_ovr,
    0x08: op_equ,
    0x09: op_neq,
    0x0A: op_gth,
    0x0B: op_lth,
    0x0C: op_jmp,
    0x0D: op_jcn,
    0x0E: op_jsr,
    0x0F: op_sth,
    0x14: op_lda,
    0x15: op_sta,
    0x17: op_deo,
    0x18: op_add,
}



def dump_state(u: Uxn):
    return {
        "mem": " ".join(hex(i) for i in u.mem[u.pc-3:u.pc+4]),
        "dev": {"console": " ".join(hex(i) for i in u.dev[0x10:0x20])},
        "pc": hex(u.pc),
        "ws": u.ws,
        "rs": u.rs,
    }

def load_image(u: Uxn, prog: bytes):
    if len(prog) > len(u.mem) - 0x100:
        raise ValueError("Program too large")
    u.mem[0x100 : len(prog)] = prog

def run_vector(u: Uxn, pc):
    u.pc = pc
    while True:
        op_mode_code = u.mem[u.pc]
        if exec_op(u, op_mode_code): 
            break

def exec_op(u: Uxn, op_mode_code):
    op_code = op_mode_code & 0x1f
    mode2 = op_mode_code >> 5 & 1
    moder = op_mode_code >> 6 & 1
    modek = op_mode_code >> 7 & 1
    op = OPS[op_code]
    if op_code:
        op_name = op.__name__
    elif modek:
        op_name = "op_lit"
    elif mode2 and moder:
        op_name = "op_jsi"
    elif moder:
        op_name = "op_jmi"
    elif mode2:
        op_name = "op_jci"
    elif not (op_code or mode2 or moder or modek):
        op_name = "op_brk"
    else:
        raise ValueError("Unreachable")

    logging.debug(f"{u.rs}, {u.ws}")
    logging.debug(f"{hex(u.pc)}: {hex(u.mem[u.pc])} {op_name} {mode2=} {moder=} {modek=}")
    u.pc += 1
    return op(u, mode2, moder, modek)
 

def set_argc(u: Uxn):
    u.dev[0x17] = len(sys.argv) - 1

def forward_args(u: Uxn):
    for i, arg in enumerate(sys.argv):
        for char in arg:
            u.dev[0x12] = ord(char)
            u.dev[0x17] = ConsoleArg
            run_vector(u, u.mem[1])
        u.dev[0x12] = ord(char)
        isLast = i + 1 == len(sys.argv)
        u.dev[0x17] = ConsoleArgEnd if isLast else ConsoleArgSpacer
        run_vector(u, ushort_peek(u.dev, ConsoleVectorPtr))

# Main

def main():
    u = Uxn()
    arg = sys.argv[1]
    if arg == "-v":
        logging.basicConfig(level=logging.DEBUG)
        program = sys.argv[2]
    else:
        program = arg

    with open(program, "rb") as rom:
        load_image(u, rom.read())
    try:
        set_argc(u)
        # forward_args(u)
        run_vector(u, Uxn.RESET)
    except Exception as e:
        pprint.pprint(dump_state(u))
        raise e


if __name__ == "__main__":
    main()
