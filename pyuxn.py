#!python3

import sys
import struct


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


def op_imm(u: "Uxn", mode2, moder, modek):
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

def op_jci(u: "Uxn"):
    if u.ws.pop():
        op_jmi(u)
    else:
        u.pc += 3

def op_jmi(u: "Uxn"):
        (hi, low) = u.mem[u.pc+1:u.pc+2]
        u.pc += (hi << 8) | low

def op_jsi(u: "Uxn"):
    u.rs.push(u.pc+2)
    op_jmi(u)

def op_lit(u: "Uxn", mode2, moder, modek):
    lit = u.mem[u.pc+1:u.pc+2+mode2]
    s = u.rs if moder else u.ws
    s.extend(lit)
    u.pc += 2


def op_inc(u: "Uxn", mode2, moder, modek):
    u.ws.push(u.ws.pop() + 1)
    u.pc += 1


def op_pop(u: "Uxn", mode2, moder, modek):
    u.ws.pop()
    u.pc += 1


def op_nip(u: "Uxn", mode2, moder, modek):
    top = u.ws.pop()
    u.ws.pop()
    u.ws.push(top)
    u.pc += 1


def op_swp(u: "Uxn", mode2, moder, modek):
    top = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(top)
    u.ws.push(bot)
    u.pc += 1


def op_rot(u: "Uxn", mode2, moder, modek):
    top = u.ws.pop()
    mid = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(bot)
    u.ws.push(top)
    u.ws.push(mid)
    u.pc += 1


def op_dup(u: "Uxn", mode2, moder, modek):
    top = u.ws.pop()
    u.ws.push(top)
    u.ws.push(top)
    u.pc += 1


def op_ovr(u: "Uxn", mode2, moder, modek):
    top = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(top)
    u.ws.push(bot)
    u.ws.push(bot)
    u.pc += 1


def op_equ(u: "Uxn", mode2, moder, modek):
    top = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(int(bot == top))
    u.pc += 1


def op_neq(u: "Uxn", mode2, moder, modek):
    top = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(int(bot != top))
    u.pc += 1


def op_gth(u: "Uxn", mode2, moder, modek):
    top = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(int(bot > top))
    u.pc += 1


def op_lth(u: "Uxn", mode2, moder, modek):
    top = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(int(bot < top))
    u.pc += 1


def op_jmp(u: "Uxn", mode2, moder, modek):
    (top,) = struct.unpack_from("@b", u.ws, len(u.ws) - 1)
    u.ws.pop()
    u.pc += top


def op_jcn(u: "Uxn", mode2, moder, modek):
    (top,) = struct.unpack_from("@b", u.ws, len(u.ws) - 1)
    u.ws.pop()
    if u.ws.pop() != 0:
        u.pc += top


def op_jsr(u: "Uxn", mode2, moder, modek):
    u.rs.extend((u.pc >> 8, u.pc & 255))
    (top,) = struct.unpack_from("@b", u.ws, len(u.ws) - 1)
    u.ws.pop()
    u.pc += top


def op_sth(u: "Uxn", mode2, moder, modek):
    (top,) = struct.unpack_from("@b", u.ws, len(u.ws) - 1)
    u.ws.pop()
    u.rs.push(top)
    u.pc += top


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
}


class Uxn:
    def __init__(self) -> None:
        self.mem = bytearray(64000)
        self.pc = 0
        self.ws = FixedSizeStack(256)
        self.rs = FixedSizeStack(256)

    def dump_state(self):
        return {
            "mem": " ".join(hex(i) for i in self.mem[self.pc-3:self.pc+3]),
            "pc": self.pc,
            "ws": self.ws,
            "rs": self.rs,
        }

    def load_image(self, prog: bytes):
        if len(prog) > len(self.mem) - 0x100:
            raise ValueError("Program too large")
        self.mem[0x100 : len(prog)] = prog

    def run(self):
        self.pc = 0x100
        while True:
            op_mode_code = self.mem[self.pc]
            op_code = op_mode_code & 0x1f
            mode2 = op_mode_code >> 5 & 1
            moder = op_mode_code >> 6 & 1
            modek = op_mode_code >> 7 & 1
            op = OPS[op_code]
            print(self.ws)
            print(hex(self.pc), ":", hex(self.mem[self.pc]), op.__name__, f"{mode2=} {moder=} {modek=}")
            if op(self, mode2, moder, modek):
                break
        print(self.ws)

    def exec_op(self, op_code):
        OPS[op_code](self)
        print(self.ws)


def main():
    uxn = Uxn()
    with open(sys.argv[1], "rb") as rom:
        uxn.load_image(rom.read())
    try:
        uxn.run()
    except Exception as e:
        print(uxn.dump_state())
        raise e


if __name__ == "__main__":
    main()
