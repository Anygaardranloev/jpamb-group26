import argparse
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Tuple

from loguru import logger

import jpamb
from jpamb import jvm

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}")


if TYPE_CHECKING:
    from fuzzer import Coverage


def to_int(v: jvm.Value) -> int:
    if v.type is jvm.Int():
        return v.value
    if v.type is jvm.Char():
        return ord(v.value)
    if v.type is jvm.Boolean():
        return 1 if v.value else 0
    raise AssertionError(f"expected int/char/bool, got {v}")


@dataclass
class PC:
    method: jvm.AbsMethodID
    offset: int

    def __iadd__(self, delta):
        self.offset += delta
        return self

    def __add__(self, delta):
        return PC(self.method, self.offset + delta)

    def __str__(self):
        return f"{self.method}:{self.offset}"


@dataclass
class Bytecode:
    suite: jpamb.Suite
    methods: dict[jvm.AbsMethodID, list[jvm.Opcode]]

    def __getitem__(self, pc: PC) -> jvm.Opcode:
        try:
            opcodes = self.methods[pc.method]
        except KeyError:
            opcodes = list(self.suite.method_opcodes(pc.method))
            self.methods[pc.method] = opcodes
        return opcodes[pc.offset]


@dataclass
class Stack[T]:
    items: list[T]

    def __bool__(self) -> bool:
        return len(self.items) > 0

    @classmethod
    def empty(cls):
        return cls([])

    def peek(self) -> T:
        return self.items[-1]

    def pop(self) -> T:
        return self.items.pop(-1)

    def push(self, value):
        self.items.append(value)
        return self

    def __str__(self):
        if not self:
            return "ϵ"
        return "".join(f"{v}" for v in self.items)


@dataclass
class Frame:
    locals: dict[int, jvm.Value]
    stack: Stack[jvm.Value]
    pc: PC

    def __str__(self):
        locals = ", ".join(f"{k}:{v}" for k, v in sorted(self.locals.items()))
        return f"<{{{locals}}}, {self.stack}, {self.pc}>"

    @staticmethod
    def from_method(method: jvm.AbsMethodID) -> "Frame":
        return Frame({}, Stack.empty(), PC(method, 0))


@dataclass
class State:
    heap: dict[int, str]
    frames: Stack[Frame]
    next_ref: int = 0
    string_pool: dict[str, int] = field(default_factory=dict)

    def __str__(self):
        return f"{self.heap} {self.frames}"


class Interpreter:
    def __init__(self, suite: jpamb.Suite, coverage: "Coverage | None" = None):
        self.suite = suite
        self.bc = Bytecode(suite, dict())
        self.coverage = coverage

    def _bin_int(self, frame, state, op):
        v2, v1 = frame.stack.pop(), frame.stack.pop()
        assert (
            v1.type == jvm.Int() and v2.type == jvm.Int()
        ), f"expected ints, got {v1}, {v2}"
        frame.stack.push(jvm.Value.int(op(v1.value, v2.value)))
        frame.pc += 1
        return state

    def alloc_string_literal(self, state: State, s: str) -> jvm.Value:
        if s in state.string_pool:
            obj = state.string_pool[s]
        else:
            obj = state.next_ref
            state.next_ref += 1
            state.string_pool[s] = obj
            state.heap[obj] = s
        return jvm.Value(jvm.Reference(), obj)

    def alloc_string_object(self, state: State, s: str) -> jvm.Value:
        obj = state.next_ref
        state.next_ref += 1
        state.heap[obj] = s
        return jvm.Value(jvm.Reference(), obj)

    def get_string(self, state: State, v: jvm.Value) -> str | None:
        if v.value is None:
            return None

        if isinstance(v.value, int):
            return state.heap[v.value]

        if isinstance(v.value, str):
            return v.value

        assert False, f"expected string ref id or literal, got {v}"

    def step(self, state: State) -> State | str:
        assert isinstance(state, State), f"expected frame but got {state}"
        frame = state.frames.peek()
        opr = self.bc[frame.pc]
        logger.debug(f"STEP {opr}\n{state}")

        if self.coverage is not None:
            self.coverage.hit_pc(frame.pc)

        match opr:
            case jvm.Push(value=v):
                if v.type == jvm.Reference() and isinstance(v.value, str | type(None)):
                    if v.value is None:
                        frame.stack.push(jvm.Value(jvm.Reference(), None))
                    else:
                        frame.stack.push(self.alloc_string_literal(state, v.value))
                else:
                    frame.stack.push(v)
                frame.pc += 1
                return state
            case jvm.Incr(index=i, amount=c):
                old_val = frame.locals.get(i, jvm.Value.int(0))
                assert (
                    old_val.type == jvm.Int()
                ), f"expected int local var, got {old_val}"
                frame.locals[i] = jvm.Value.int(old_val.value + c)
                frame.pc += 1
                return state
            case jvm.Pop():
                frame.stack.pop()
                frame.pc += 1
                return state
            case jvm.Load(type=_t, index=i):
                frame.stack.push(frame.locals[i])
                frame.pc += 1
                return state
            case jvm.Store(type=_t, index=i):
                v = frame.stack.pop()
                frame.locals[i] = v
                frame.pc += 1
                return state
            case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Div):
                v2, v1 = frame.stack.pop(), frame.stack.pop()
                assert v1.type is jvm.Int(), f"expected int, but got {v1}"
                assert v2.type is jvm.Int(), f"expected int, but got {v2}"
                if v2.value == 0:
                    return "divide by zero"
                frame.stack.push(jvm.Value.int(v1.value // v2.value))
                frame.pc += 1
                return state
            case jvm.Return(type=jvm.Int()):
                v1 = frame.stack.pop()
                state.frames.pop()
                if state.frames:
                    frame = state.frames.peek()
                    frame.stack.push(v1)
                    frame.pc += 1
                    return state
                else:
                    return "ok"
            case jvm.Ifz(condition=cond, target=t):
                v = frame.stack.pop()
                val = v.value
                if isinstance(val, bool):
                    val = 1 if val else 0
                elif not isinstance(val, int):
                    raise AssertionError(f"ifz expects int/bool-like, got {v}")
                c = str(cond)  # e.g., 'eq','ne','gt','ge','lt','le','z','nz'
                if c in ("eq", "z"):
                    jump = val == 0
                elif c in ("ne", "nz"):
                    jump = val != 0
                elif c == "gt":
                    jump = val > 0
                elif c == "ge":
                    jump = val >= 0
                elif c == "lt":
                    jump = val < 0
                elif c == "le":
                    jump = val <= 0
                else:
                    raise NotImplementedError(f"Unknown Ifz condition: {c}")
                frame.pc = PC(frame.pc.method, t) if jump else (frame.pc + 1)
                return state
            case jvm.If(condition=cond, target=t):
                v2 = frame.stack.pop()
                v1 = frame.stack.pop()
                c = str(cond)
                if c == "is":
                    ok = v1.type == v2.type and v1.value == v2.value
                else:
                    i1 = to_int(v1)
                    i2 = to_int(v2)

                    if c == "gt":
                        ok = i1 > i2
                    elif c == "ge":
                        ok = i1 >= i2
                    elif c == "lt":
                        ok = i1 < i2
                    elif c == "le":
                        ok = i1 <= i2
                    elif c == "eq":
                        if self.coverage is not None:
                            self.coverage.log_int32_cmp(frame.pc, i1, i2)
                        ok = i1 == i2
                    elif c == "ne":
                        if self.coverage is not None:
                            self.coverage.log_int32_cmp(frame.pc, i1, i2)
                        ok = i1 != i2
                    else:
                        ok = False
                frame.pc = PC(frame.pc.method, t) if ok else (frame.pc + 1)
                return state
            case jvm.Goto(target=t):
                frame.pc = PC(frame.pc.method, t)
                return state
            case jvm.Get(static=True):
                frame.stack.push(jvm.Value.int(0))
                frame.pc += 1
                return state
            case jvm.Dup():
                frame.stack.push(frame.stack.peek())
                frame.pc += 1
                return state
            case jvm.Dup(depth=_d):
                frame.stack.push(frame.stack.peek())
                frame.pc += 1
                return state
            case jvm.New(classname=_cls):
                if str(_cls) == "java/lang/String":
                    v = self.alloc_string_object(state, "")
                    frame.stack.push(v)
                else:
                    frame.stack.push(jvm.Value.int(0))
                frame.pc += 1
                return state
            case jvm.InvokeSpecial(method=m):
                ms = str(m)
                if ms.startswith("java/lang/String.<init>:"):
                    _cls_and_name, _, desc = ms.partition(":")

                    if desc.startswith("(Ljava/lang/String;)"):
                        arg = frame.stack.pop()
                        this = frame.stack.pop()
                        s_arg = self.get_string(state, arg)
                        if s_arg is None:
                            s_arg = ""
                        assert isinstance(
                            this.value, int
                        ), f"expected string ref id for this, got {this}"
                        state.heap[this.value] = s_arg

                    elif desc.startswith("()"):
                        this = frame.stack.pop()
                        assert isinstance(
                            this.value, int
                        ), f"expected string ref id for this, got {this}"
                        state.heap[this.value] = ""

                    elif desc.startswith("([C)"):
                        arg = frame.stack.pop()
                        this = frame.stack.pop()
                        assert (
                            arg.type == jvm.Reference()
                        ), f"expected char array ref, got {arg}"
                        assert isinstance(
                            arg.value, int
                        ), f"expected char array ref id, got {arg}"
                        char_array_ref = arg.value
                        char_array = state.heap.get(char_array_ref)
                        if char_array is None:
                            s_arg = ""
                        else:
                            s_arg = "".join(char_array)
                        assert isinstance(
                            this.value, int
                        ), f"expected string ref id for this, got {this}"
                        state.heap[this.value] = s_arg
                    else:
                        raise NotImplementedError(
                            f"Don't know how to handle: {ms} with desc {desc}"
                        )

                    frame.pc += 1
                    return state
                frame.pc += 1
                return state
            case jvm.InvokeVirtual(method=m):
                ms = str(m)
                if ms.startswith("java/lang/String."):
                    class_and_name, _, desc = ms.partition(":")
                    _cls, _, name = class_and_name.rpartition(".")
                    match name:
                        case "length":  # desc == "()I"
                            recv = frame.stack.pop()
                            if recv.value is None:
                                return "null pointer"
                            s = self.get_string(state, recv)
                            assert isinstance(
                                s, str
                            ), f"expected String receiver, got {recv}"
                            frame.stack.push(jvm.Value.int(len(s)))
                            frame.pc += 1
                            return state
                        case "concat":
                            arg = frame.stack.pop()
                            recv = frame.stack.pop()
                            if recv.value is None:
                                return "null pointer"
                            s_recv = self.get_string(state, recv)
                            assert isinstance(
                                s_recv, str
                            ), f"expected String receiver, got {recv}"
                            if arg.value is None:
                                s_arg = "null"
                            else:
                                s_arg = self.get_string(state, arg)
                                assert isinstance(
                                    s_arg, str
                                ), f"expected String argument, got {arg}"
                            frame.stack.push(
                                self.alloc_string_object(state, s_recv + s_arg)
                            )
                            frame.pc += 1
                            return state
                        case "equals":
                            other = frame.stack.pop()
                            recv = frame.stack.pop()
                            s_recv = self.get_string(state, recv)
                            s_other = self.get_string(state, other)
                            if s_recv is None or s_other is None:
                                is_equal = False
                            else:
                                is_equal = s_recv == s_other

                            if self.coverage is not None:
                                self.coverage.log_str_cmp(frame.pc, s_recv, s_other)

                            frame.stack.push(jvm.Value(jvm.Boolean(), is_equal))
                            frame.pc += 1
                            return state
                        case "equalsIgnoreCase":
                            other = frame.stack.pop()
                            recv = frame.stack.pop()
                            s_recv = self.get_string(state, recv)
                            s_other = self.get_string(state, other)
                            if s_recv is None or s_other is None:
                                is_equal = False
                            else:
                                is_equal = s_recv.lower() == s_other.lower()

                            if self.coverage is not None:
                                self.coverage.log_str_cmp(
                                    frame.pc, s_recv, s_other, case_sensitive=False
                                )
                            frame.stack.push(jvm.Value(jvm.Boolean(), is_equal))
                            frame.pc += 1
                            return state
                        case "charAt":
                            index = frame.stack.pop()
                            recv = frame.stack.pop()
                            assert (
                                index.type is jvm.Int()
                            ), f"expected int index, got {index}"
                            i = index.value
                            if recv.value is None:
                                return "out of bounds"
                            s = self.get_string(state, recv)
                            assert isinstance(
                                s, str
                            ), f"expected String receiver, got {recv}"
                            if len(s) == 0:
                                return "assertion error"
                            if i < 0 or i >= len(s):
                                return "out of bounds"
                            ch = s[i]
                            frame.stack.push(jvm.Value(jvm.Char(), ch))
                            frame.pc += 1
                            return state
                        case "substring":
                            end = frame.stack.pop()
                            start = frame.stack.pop()
                            recv = frame.stack.pop()
                            assert (
                                start.type is jvm.Int() and end.type is jvm.Int()
                            ), f"expected int indices, got {start}, {end}"
                            if recv.value is None:
                                return "out of bounds"
                            s = self.get_string(state, recv)
                            assert isinstance(
                                s, str
                            ), f"expected String receiver, got {recv}"
                            i, j = start.value, end.value
                            if i < 0 or j < i or j > len(s):
                                return "out of bounds"
                            result = s[i:j]
                            frame.stack.push(self.alloc_string_object(state, result))
                            frame.pc += 1
                            return state
                        case name:
                            raise NotImplementedError(
                                f"Don't know how to handle: {name}"
                            )
                else:  # not a string
                    frame.pc += 1
                    return state
            case jvm.InvokeStatic(method=_m):
                frame.pc += 1
                return state
            case jvm.Throw():
                exc = frame.stack.pop()
                if exc.value is None:
                    return "null pointer"

                return "assertion error"
            case jvm.Return(type=None):
                state.frames.pop()
                if state.frames:
                    caller = state.frames.peek()
                    caller.pc += 1
                    return state
                else:
                    return "ok"
            case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Mul):
                return self._bin_int(frame, state, lambda a, b: a * b)

            case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Add):
                return self._bin_int(frame, state, lambda a, b: a + b)

            case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Sub):
                return self._bin_int(frame, state, lambda a, b: a - b)
            case a:
                raise NotImplementedError(f"Don't know how to handle: {a!r}")

    def run_method(
        self,
        methodid: jvm.AbsMethodID,
        method_args: Tuple[jvm.Value, ...],
        max_steps: int = 1000,
    ) -> str:
        frame = Frame.from_method(methodid)
        for i, v in enumerate(method_args):
            frame.locals[i] = v

        state = State({}, Stack.empty().push(frame))

        for _ in range(max_steps):
            state = self.step(state)
            if isinstance(state, str):
                return state
        return "*"


def main():
    example = """Example usage:
    uv run solutions/interpreter.py "jpamb.cases.Simple.assertInteger:(I)V" "(0)"
    uv run solutions/interpreter.py "jpamb.cases.Strings.stringLenSometimesNull:(I)V" "(100)"
"""

    ap = argparse.ArgumentParser(
        epilog=example, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("methodid", type=str, help="Method ID to execute")
    ap.add_argument(
        "input",
        type=str,
        help="Input values as a comma-separated string wrapped in parentheses",
    )
    ap.add_argument(
        "--max-steps", type=int, default=1000, help="Maximum number of steps"
    )
    args = ap.parse_args()

    try:
        methodid = jvm.AbsMethodID.decode(args.methodid)
    except Exception as e:
        logger.error(f"Failed to decode method ID: {e}")
        return

    try:
        method_args = jpamb.Input.decode(args.input)
    except Exception as e:
        logger.error(f"Failed to decode input: {e}")
        return

    suite = jpamb.Suite()
    interpreter = Interpreter(suite, None)
    result = interpreter.run_method(methodid, method_args.values, args.max_steps)

    print(result)


if __name__ == "__main__":
    main()
