import jpamb
from jpamb import jvm
from dataclasses import dataclass

import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}")

methodid, input = jpamb.getcase()

def make_string_value(s: str) -> jvm.Value:
    return jvm.Value(jvm.Reference(), s)

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


suite = jpamb.Suite()
bc = Bytecode(suite, dict())


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
    heap: dict[int, jvm.Value]
    frames: Stack[Frame]

    def __str__(self):
        return f"{self.heap} {self.frames}"

def _bin_int(frame, state, op):
    v2, v1 = frame.stack.pop(), frame.stack.pop()
    assert v1.type == jvm.Int() and v2.type == jvm.Int(), f"expected ints, got {v1}, {v2}"
    frame.stack.push(jvm.Value.int(op(v1.value, v2.value)))
    frame.pc += 1
    return state

def step(state: State) -> State | str:
    assert isinstance(state, State), f"expected frame but got {state}"
    frame = state.frames.peek()
    opr = bc[frame.pc]
    logger.debug(f"STEP {opr}\n{state}")
    match opr:
        case jvm.Push(value=v):
            frame.stack.push(v)
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
            if c in ("eq", "z"): jump = (val == 0)
            elif c in ("ne", "nz"): jump = (val != 0)
            elif c == "gt": jump = (val >  0)
            elif c == "ge": jump = (val >= 0)
            elif c == "lt": jump = (val <  0)
            elif c == "le": jump = (val <= 0)
            else:
                raise NotImplementedError(f"Unknown Ifz condition: {c}")
            frame.pc = PC(frame.pc.method, t) if jump else (frame.pc + 1)
            return state
        case jvm.If(condition=cond, target=t):
            v2 = frame.stack.pop()
            v1 = frame.stack.pop()
            c = str(cond)
            if c == "is":
                assert v1.type is jvm.Reference() and v2.type is jvm.Reference(), f"expected refs, got {v1}, {v2}"

                is_new1 = getattr(v1, "_is_new_string", False)
                is_new2 = getattr(v2, "_is_new_string", False)

                if is_new1 or is_new2:
                    ok = False
                else:
                    ok = (v1 is v2) or (v1.type is v2.type and v1.value == v2.value)
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
                    ok = i1 == i2
                elif c == "ne":
                    ok = i1 != i2
                else:
                    raise NotImplementedError(f"Unhandled if condition: {c}")
            if ok:
                frame.pc = PC(frame.pc.method, t)
            else:
                frame.pc += 1
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
            frame.stack.push(jvm.Value.int(0))
            frame.pc += 1
            return state
        case jvm.InvokeSpecial(method=_m):
            frame.pc += 1
            return state
        case jvm.InvokeVirtual(method=m):
            ms = str(m) 
            if ms.startswith("java/lang/String."):
                class_and_name, _, desc = ms.partition(":")
                _cls, _, name = class_and_name.rpartition(".")
                match name:
                    case "length": # desc == "()I"
                        recv = frame.stack.pop()
                        if recv.value is None:
                            return "null pointer"
                        assert isinstance(
                            recv.value, str
                        ), f"expected String receiver, got {recv}"
                        frame.stack.push(jvm.Value.int(len(recv.value)))
                        frame.pc += 1
                        return state
                    case "concat":
                        arg = frame.stack.pop()
                        recv = frame.stack.pop()
                        assert isinstance(
                            recv.value, str
                        ), f"expected String receiver, got {recv}"
                        assert isinstance(
                            arg.value, str
                        ), f"expected String argument, got {arg}"
                        frame.stack.push(make_string_value(recv.value + arg.value))
                        frame.pc += 1
                        return state
                    case "equals":
                        other = frame.stack.pop()
                        recv = frame.stack.pop()
                        is_equal = (
                            isinstance(recv.value, str)
                            and isinstance(other.value, str)
                            and recv.value == other.value
                        )
                        frame.stack.push(jvm.Value(jvm.Boolean(), is_equal))
                        frame.pc += 1
                        return state
                    case "equalsIgnoreCase":
                        other = frame.stack.pop()
                        recv = frame.stack.pop()
                        is_equal = (
                            isinstance(recv.value, str)
                            and isinstance(other.value, str)
                            and recv.value.lower() == other.value.lower()
                        )
                        frame.stack.push(jvm.Value(jvm.Boolean(), is_equal))
                        frame.pc += 1
                        return state
                    case "charAt":
                        index = frame.stack.pop()
                        recv = frame.stack.pop()
                        assert index.type is jvm.Int(), f"expected int index, got {index}"
                        if recv.value is None or not isinstance(recv.value, str):
                            return "out of bounds"
                        s = recv.value
                        i = index.value
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
                        if recv.value is None or not isinstance(recv.value, str):
                            return "out of bounds"
                        s = recv.value
                        i, j = start.value, end.value
                        if i < 0 or j < i or j > len(s):
                            return "out of bounds"
                        result = s[i:j]
                        frame.stack.push(make_string_value(result))
                        frame.pc += 1
                        return state
                    case name:
                        raise NotImplementedError(f"Don't know how to handle: {name}")
            else: # not a string
                frame.pc += 1
                return state
        case jvm.InvokeStatic(method=_m):
            frame.pc += 1
            return state
        case jvm.Throw():
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
            return _bin_int(frame, state, lambda a, b: a * b)

        case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Add):
            return _bin_int(frame, state, lambda a, b: a + b)

        case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Sub):
            return _bin_int(frame, state, lambda a, b: a - b)
        case a:
            raise NotImplementedError(f"Don't know how to handle: {a!r}")

frame = Frame.from_method(methodid)
for i, v in enumerate(input.values):
    frame.locals[i] = v

state = State({}, Stack.empty().push(frame))

for x in range(1000):
    state = step(state)
    if isinstance(state, str):
        print(state)
        break
else:
    print("*")