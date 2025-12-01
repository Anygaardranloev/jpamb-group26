import argparse
import sys
import jpamb
from jpamb import jvm
from dataclasses import dataclass, field
import unicodedata
import copy
from typing import Tuple
from loguru import logger
from dataclasses import dataclass
from typing import FrozenSet, Literal

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}")

Sign = Literal["L", "N", "S"]
Encoding = Literal["latin1", "utf16"]

@dataclass(frozen=True)
class StringSign:
    signs: FrozenSet[Sign]
    encodings: FrozenSet[Encoding]
    length: int

    def __contains__(self, s: str) -> bool:
        
        for ch in s:
            if StringSign.sign_of_char(ch) not in self.signs:
                return False
            if StringSign.encoding_of_char(ch) not in self.encodings:
                return False
        return True

    def __and__(self, other: "StringSign") -> "StringSign":
        return StringSign(
            signs=self.signs & other.signs,
            encodings=self.encodings & other.encodings,
            length=max(self.length, other.length)
        )

    def __or__(self, other: "StringSign") -> "StringSign":
        return StringSign(
            signs=self.signs | other.signs,
            encodings=self.encodings | other.encodings,
            length=min(self.length, other.length))
    
    def __le__(self, other: "StringSign") -> bool:
        return (
            self.signs.issubset(other.signs) and
            self.encodings.issubset(other.encodings) and
            self.length <= other.length
        )


    @classmethod
    def abstract(cls, string: str) -> "StringSign":
        sign_set: set[Sign] = set()
        enc_set: set[Encoding] = set()

        for ch in string:
            sign_set.add(StringSign.sign_of_char(ch))
            enc_set.add(StringSign.encoding_of_char(ch))

        return cls(frozenset(sign_set), frozenset(enc_set), len(string))
    
    @classmethod
    def newStringSign(cls, signs: frozenset[Sign], encodings: frozenset[Encoding], length: int) -> "StringSign":
        return cls(signs, encodings, length)

    @staticmethod
    def sign_of_char(ch: str) -> Sign:

        cat = unicodedata.category(ch)
        if cat.startswith("L"):
            return "L"
        if cat.startswith("N"):
            return "N"
        return "S"

    @staticmethod
    def encoding_of_char(ch: str) -> Encoding:

        cp = ord(ch)
        if cp <= 0xFF:
            return "latin1"
        return "utf16"
        
    def __str__(self) -> str:
        signs = ", ".join(sorted(self.signs))
        encs  = ", ".join(sorted(self.encodings))
        return f"string-[{signs}]-[{encs}]-{self.length}"

    __repr__ = __str__

class SignSet:

    signSet: set[StringSign]

    def __init__(self, signSet: set[StringSign]):
        self.signSet = signSet

    def __contains__(self, member : StringSign) -> bool: 
        if (member in self.signSet): 
            return True
        return False

    @classmethod
    def abstract(cls, strings: list[str]) -> "SignSet":
        sign_set: set[StringSign] = set()

        for string in strings:
            sign_set.add(StringSign.abstract(string))

        return cls(sign_set)
    
    def __and__(self, other: "SignSet") -> "SignSet":
        result = set()
        for s1 in self.signSet:
            for s2 in other.signSet:
                result.add(s1 & s2)
        return SignSet(result)

    def __or__(self, other: "SignSet") -> "SignSet":
        result = set()
        for s1 in self.signSet:
            for s2 in other.signSet:
                result.add(s1 | s2)
        return SignSet(result)


class StringOperation:

    @staticmethod
    def nullPointer(string: StringSign):
        return string == None
    
    @staticmethod
    def getLength(string: StringSign):
        return string.length
    
    @staticmethod
    def getChar(string: StringSign, place: int):
        if place > 0 and string.length > place:
            return StringSign.newStringSign(string.signs,string.encodings,1)
        else:
            return "out of bounds"

    @staticmethod
    def equals(string: StringSign, other: StringSign):
        if string.encodings != other.encodings or string.signs != other.signs or string.length != other.length:
            return "assertion error"
        else:
            return "maybe"
        
    @staticmethod
    def subString(string: StringSign, beginIndex: int, endIndex: int ):
        if beginIndex < -1 or endIndex > string.length or beginIndex > endIndex:
            return "out of bounds"
        
        newLength = string.length - (endIndex - beginIndex)

        return StringSign.newStringSign(string.signs,string.encodings, newLength)
    
    @staticmethod
    def concat(string: StringSign, other: StringSign):

        if string == None or other == None:
            return "null pointer"

        signs = string.signs.union(other.signs)
        encodings = string.encodings.union(other.encodings)
        length = string.length + other.length

        return StringSign.newStringSign(signs,encodings,length)

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
    heap: dict[int, StringSign]
    frames: Stack[Frame]
    next_ref: int = 0
    string_pool: dict[StringSign, int] = field(default_factory=dict)

    def copy(self):
        return State(copy.deepcopy(self.heap), copy.deepcopy(self.frames))

    def __str__(self):
        return f"{self.heap} {self.frames}"

def to_int(v: jvm.Value) -> int:
    if isinstance(v,int):
        return v
    if v.type is jvm.Int():
        return v.value
    if v.type is jvm.Char():
        return ord(v.value)
    if v.type is jvm.Boolean():
        return 1 if v.value else 0
    raise AssertionError(f"expected int/char/bool, got {v}")

class Interpreter:

    def __init__(self, suite: jpamb.Suite):
        self.suite = suite
        self.bc = Bytecode(suite, dict())
    
    def _bin_int(self, frame: Frame, state: State, op):
        v2, v1 = frame.stack.pop(), frame.stack.pop()
        if isinstance(v1,int) and isinstance(v2, int):
            frame.stack.push(jvm.Value.int(op(v1, v2)))

        elif isinstance(v1,jvm.Value) and isinstance(v2, jvm.Value):
            assert (
                v1.type == jvm.Int() and v2.type == jvm.Int()
            ), f"expected ints, got {v1}, {v2}"
            frame.stack.push(jvm.Value.int(op(v1.value, v2.value)))
        frame.pc += 1
        return state

    def alloc_string_literal(self, state: State, s: StringSign) -> jvm.Value:
        if s in state.string_pool:
            obj = state.string_pool[s]
        else:
            obj = state.next_ref
            state.next_ref += 1
            state.string_pool[s] = obj
            state.heap[obj] = s
        return jvm.Value(jvm.Reference(), obj)

    def alloc_string_object(self, state: State, s: StringSign) -> jvm.Value:
        obj = state.next_ref
        state.next_ref += 1
        state.heap[obj] = s
        return jvm.Value(jvm.Reference(), obj)
    
    def get_stringSign(self, state: State, v: jvm.Value) -> StringSign:
        if isinstance(v, StringSign):
            return v

        if v.value is None:
            return None

        if isinstance(v.value, int):
            return state.heap[v.value]

        if isinstance(v.value, StringSign):
            return v.value

        assert False, f"expected string ref id or literal, got {v}"

    def step(self, state : State) -> State | str:
        assert isinstance(state, State), f"expected frame but got {state}"
        frame = state.frames.peek()
        opr = self.bc[frame.pc]
        logger.debug(f"STEP {opr}\n{state}")
        
        match opr:
            case jvm.Push(value=v):
                if v.type == jvm.Reference() and isinstance(v.value, str | type(None)):
                    if v.value is None:
                        frame.stack.push(jvm.Value(jvm.Reference(), None))
                    else:
                        frame.stack.push(self.alloc_string_literal(state, StringSign.abstract(v.value)))
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
                
            case jvm.Return(type=_t):
                state.frames.pop()
                if state.frames:
                    frame = state.frames.peek()
                    frame.pc += 1
                    return state
                else:
                    return "ok"
                    
            case jvm.Get(static=is_static, field=field):
                frame.stack.push(jvm.Value.int(0))
                frame.pc += 1
                return state
            
            case jvm.Get(static=True):
                frame.stack.push(jvm.Value.int(0))
                frame.pc += 1
                return state
            
            case jvm.New(classname=_cls):
                if str(_cls) == "java/lang/String":
                    v = self.alloc_string_object(state, StringSign.abstract(""))
                    frame.stack.push(v)
                else:
                    frame.stack.push(jvm.Value.int(0))
                frame.pc += 1
                return state

            case jvm.Dup():
                v = frame.stack.peek()
                frame.stack.push(v)
                frame.pc += 1
                return state
            
            case jvm.Dup(depth=_d):
                frame.stack.push(frame.stack.peek())
                frame.pc += 1
                return state
            
            case jvm.Store(type=_t, index=i):
                v = frame.stack.pop()
                frame.locals[i] = v
                frame.pc += 1
                return state
            
            case jvm.Goto(target=t):
                frame.pc = PC(frame.pc.method, t)
                return state
            
            case jvm.Ifz(condition=cond, target=t):
                v = frame.stack.pop()
                val = 0
                if not isinstance(v,jvm.Value):
                    if isinstance(v, bool):
                        val = 1 if val else 0
                    elif isinstance(v, int):
                        val = v
                    else:
                        raise AssertionError(f"ifz expects int/bool-like, got {v}")
                else:
                    val = v.value
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
                    if isinstance(v1,jvm.Value) and isinstance(v2,jvm.Value):
                        ok = v1.type == v2.type and v1.value == v2.value
                    else:
                        ok = v1 == v2
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
                        ok = False
                frame.pc = PC(frame.pc.method, t) if ok else (frame.pc + 1)
                return state
            
            case jvm.InvokeSpecial(method=mid):
                method_name = mid.extension.name
                if method_name == "<init>":
                    # Simulate object creation (same as jvm.New)
                    obj_ref = state.next_ref
                    state.next_ref += 1
                    state.heap[obj_ref] = StringSign.abstract("")
                    frame.stack.push(state.heap[obj_ref])
                    frame.pc += 1
                    return state
                else:
                    # Handle other special methods
                    frame.pc += 1
                    return state
                
            case jvm.InvokeVirtual(method=m):
                ms = str(m)
                if ms.startswith("java/lang/String."):
                    class_and_name, _, desc = ms.partition(":")
                    _cls, _, name = class_and_name.rpartition(".")
                    match name:
                        case "length":
                            recv = frame.stack.pop()
                            if recv is None:
                                return "null pointer"
                            
                            value = self.get_stringSign(state,recv)

                            if value is None:
                                return "null pointer"
                            
                            frame.stack.push(StringOperation.getLength(value))
                            frame.pc += 1
                            return state
                        case "concat":
                            arg = frame.stack.pop()
                            recv = frame.stack.pop()

                            if recv.value is None or arg.value is None:
                                return "null pointer"
                            
                            value1 = self.get_stringSign(state, arg)
                            value2 = self.get_stringSign(state,recv)

                            assert isinstance(value1, StringSign) and isinstance(value2,StringSign), f"expected StringSign argument, got 1. {arg}, 2. {recv}"

                            frame.stack.push(
                                self.alloc_string_object(state, StringOperation.concat(value1,value2))
                            )
                            frame.pc += 1
                            return state
                        case "equals":
                            arg = frame.stack.pop()
                            recv = frame.stack.pop()

                            value1 = self.get_stringSign(state, arg)
                            value2 = self.get_stringSign(state,recv)

                            if value1 is None or value2 is None:
                                is_equal = False
                            else:
                                result = StringOperation.equals(value1,value2)

                                if result == "assertion error":
                                    is_equal = False

                                elif result == "maybe":
                                    is_equal = False
                            
                            frame.stack.push(jvm.Value(jvm.Boolean(), is_equal))
                            frame.pc += 1
                            return state

                        case "equalsIgnoreCase": # same as equals
                            arg = frame.stack.pop()
                            recv = frame.stack.pop()

                            value1 = self.get_stringSign(state, arg)
                            value2 = self.get_stringSign(state,recv)

                            if value1 is None or value2 is None:
                                is_equal = False
                            else:
                                result = StringOperation.equals(value1,value2)

                                if result == "assertion error":
                                    is_equal = False

                                elif result == "maybe":
                                    is_equal = False
                            
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
                            assert isinstance(
                                i, int
                            ), f"expected int receiver, got {recv}"

                            if recv.value is None:
                                return "out of bounds"
                            
                            stringSign = self.get_stringSign(state,recv)
                            assert isinstance(
                                stringSign, StringSign
                            ), f"expected String receiver, got {recv}"
                            
                            result = StringOperation.getChar(stringSign,i)

                            if isinstance(result,StringSign):
                                frame.stack.push(self.alloc_string_object(state,result))
                                frame.pc += 1
                                return state
                            else:
                                return "out of bounds"

                        case "substring":
                            end = frame.stack.pop()
                            start = frame.stack.pop()
                            recv = frame.stack.pop()

                            beginIndex, endIndex = start.value, end.value

                            assert isinstance(beginIndex, int) and isinstance(endIndex,int),f"expected int indices, got {start}, {end}"

                            if recv.value is None:
                                return "out of bounds"
                            
                            stringSign = self.get_stringSign(state,recv)

                            assert isinstance(
                                stringSign, StringSign
                            ), f"expected String receiver, got {recv}"

                            result = StringOperation.subString(stringSign,beginIndex,endIndex)
                            
                            if isinstance(result,StringSign):
                                frame.stack.push(self.alloc_string_object(state,result))
                                frame.pc += 1
                                return state
                            else:
                                return "out of bounds"
                            
                        case name:
                            raise NotImplementedError(
                                f"Don't know how to handle: {name}"
                            )
                else:  # not a string
                    frame.pc += 1
                    return state
            case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Mul):
                return self._bin_int(frame, state, lambda a, b: a * b)

            case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Add):
                return self._bin_int(frame, state, lambda a, b: a + b)

            case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Sub):
                return self._bin_int(frame, state, lambda a, b: a - b)

            case jvm.Throw():
                return "assertion error"
            
            case a:
                raise NotImplementedError(f"Don't know how to handle: {a!r}")
    
    def run_all(self, initial: State, max_steps: int = 1000) -> str:
        """Runs symbolic execution until all branches terminate or max_steps reached."""
        
        state = initial

        for _ in range(max_steps):
            state = self.step(state)
            if isinstance(state, str):
                return state
        return "*"



def createState(methodid: jvm.AbsMethodID, method_args: Tuple[jvm.Value, ...]) -> State:
    
    frame = Frame.from_method(methodid)
    for i, v in enumerate(method_args):
        frame.locals[i] = v

    return State({}, Stack.empty().push(frame))

def main():
    example = """Example usage:
    uv run solutions/abstract_string_interpreter.py "jpamb.cases.Strings.stringEqualsLiteralFails:()V" "()"
    uv run solutions/abstract_string_interpreter.py "jpamb.cases.Strings.stringLenSometimesNull:(I)V" "(100)"
    uv run jpamb interpret -W --filter Strings solutions/abstract_string_interpreter.py
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
    interpreter = Interpreter(suite)

    state = createState(methodid,method_args.values)
    result = interpreter.run_all(state)

    print(result)

if __name__ == "__main__":
    main()
