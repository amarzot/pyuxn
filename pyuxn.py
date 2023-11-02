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


def op_brk(_: "Uxn"):
    return 1


def op_lit(u: "Uxn"):
    u.ws.push(u.mem[u.pc])
    u.pc += 1


def op_inc(u: "Uxn"):
    u.ws.push(u.ws.pop() + 1)


def op_pop(u: "Uxn"):
    u.ws.pop()


def op_nip(u: "Uxn"):
    top = u.ws.pop()
    u.ws.pop()
    u.ws.push(top)


def op_swp(u: "Uxn"):
    top = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(top)
    u.ws.push(bot)


def op_rot(u: "Uxn"):
    top = u.ws.pop()
    mid = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(bot)
    u.ws.push(top)
    u.ws.push(mid)


def op_dup(u: "Uxn"):
    top = u.ws.pop()
    u.ws.push(top)
    u.ws.push(top)


def op_ovr(u: "Uxn"):
    top = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(top)
    u.ws.push(bot)
    u.ws.push(bot)


def op_equ(u: "Uxn"):
    top = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(int(bot == top))


def op_neq(u: "Uxn"):
    top = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(int(bot != top))


def op_gth(u: "Uxn"):
    top = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(int(bot > top))


def op_lth(u: "Uxn"):
    top = u.ws.pop()
    bot = u.ws.pop()
    u.ws.push(int(bot < top))


def op_jmp(u: "Uxn"):
    (top,) = struct.unpack_from("@b", u.ws, len(u.ws) - 1)
    u.ws.pop()
    u.pc += top - 1


def op_jcn(u: "Uxn"):
    (top,) = struct.unpack_from("@b", u.ws, len(u.ws) - 1)
    u.ws.pop()
    if u.ws.pop() != 0:
        u.pc += top - 1


def op_jsr(u: "Uxn"):
    u.rs.extend((u.pc >> 8, u.pc & 255))
    (top,) = struct.unpack_from("@b", u.ws, len(u.ws) - 1)
    u.ws.pop()
    u.pc += top - 1


def op_sth(u: "Uxn"):
    (top,) = struct.unpack_from("@b", u.ws, len(u.ws) - 1)
    u.ws.pop()
    u.rs.push(top)
    u.pc += top - 1


OPS = {
    0x00: op_brk,
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
            mode2 = op_mode_code & 0x20
            moder = op_mode_code & 0x40
            modek = op_mode_code & 0x80
            if op_code:
                if modek:
                    op=op_lit
            else:
                op = OPS[op_code]
            print(self.ws)
            print(hex(self.pc), ":", hex(self.mem[self.pc]), op.__name__, end="")
            if op is op_lit:
                print(" ", hex(self.mem[self.pc + 1]))
            else:
                print()

            self.pc += 1
            if op(self):
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
