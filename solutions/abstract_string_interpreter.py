import sys
import jpamb
from jpamb import jvm
from dataclasses import dataclass
from collections.abc import Iterable
import unicodedata
import copy
from typing import Tuple, Union
from collections import deque
from loguru import logger
from dataclasses import dataclass
from typing import FrozenSet, Literal

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}")

Sign = Literal["letters", "numbers", "symbols"]
Encoding = Literal["latin1", "utf16"]

@dataclass(frozen=True)
class StringSign:
    signs: FrozenSet[Sign]
    encodings: FrozenSet[Encoding]
    length: int

    def __contains__(self, s: str) -> bool:
        """All chars in the string must match both sign and encoding."""
        for ch in s:
            if StringSign.sign_of_char(ch) not in self.signs:
                return False
            if StringSign.encoding_of_char(ch) not in self.encodings:
                return False
        return True

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
            return "letters"
        if cat.startswith("N"):
            return "numbers"
        return "symbols"

    @staticmethod
    def encoding_of_char(ch: str) -> Encoding:
        # Python str gives full Unicode codepoints.
        cp = ord(ch)
        if cp <= 0xFF:
            return "latin1"
        return "utf16"
        
    def __str__(self) -> str:
        signs = ", ".join(sorted(self.signs))
        encs  = ", ".join(sorted(self.encodings))
        return f"<StringSign signs=[{signs}] encodings=[{encs}] length={self.length}>"

    __repr__ = __str__

@dataclass(frozen=True)
class SignSet:
    stringSet: FrozenSet[StringSign]

    @classmethod
    def abstract(cls, strings: set[str]) -> "SignSet":
        
        stringSet = frozenset(StringSign.abstract(s) for s in strings)

        return cls(stringSet)
    
    # Lattice ops
    def join(self, other: "SignSet") -> "SignSet":
        # join is union of abstractions
        if self is BOTTOM:
            return other
        if other is BOTTOM:
            return self

        return SignSet(self.stringSet | other.stringSet)

    def meet(self, other: "SignSet") -> "SignSet":
        # meet is intersection of abstractions
        if self is TOP:
            return other
        if other is TOP:
            return self

        return SignSet(self.stringSet & other.stringSet)

    def is_leq(self, other: "SignSet") -> bool:
        # self <= other if all abstractions in self are in other
        return self.stringSet <= other.stringSet
    
    def __str__(self) -> str:
        if not self.stringSet:
            return "<SignSet ∅>"

        parts = "\n  ".join(str(s) for s in sorted(self.stringSet, key=lambda x: x.length))
        return f"<SignSet {{\n  {parts}\n}}>"

    __repr__ = __str__

BOTTOM = SignSet(frozenset())

TOP = SignSet(
    frozenset({
        StringSign(
            signs=frozenset({"letters", "numbers", "symbols"}),
            encodings=frozenset({"latin1", "utf16"}),
            length=-1 # -1 = ANY length
        )
    })
)

class StringOperation:

    @staticmethod
    def nullPointer(string: StringSign):
        return string == None
    
    @staticmethod
    def getLength(string: StringSign):
        return string.length
    
    @staticmethod
    def getChar(string: StringSign, place: int):
        if string.length > place:
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

    def copy(self):
        return State(copy.deepcopy(self.heap), copy.deepcopy(self.frames))

    def __str__(self):
        return f"{self.heap} {self.frames}"

class Interpreter:

    def __init__(self, suite: jpamb.Suite):
        self.suite = suite
        self.bc = Bytecode(suite, dict())

    def alloc_string_object(self, state: State, s: StringSign) -> jvm.Value:
        obj = state.next_ref
        state.next_ref += 1
        state.heap[obj] = s
        return jvm.Value(jvm.Reference(), obj)
    
    def get_stringSign(self, state: State, v: jvm.Value) -> StringSign:
        if v.value is None:
            return None

        if isinstance(v.value, int):
            return state.heap[v.value]

        if isinstance(v.value, StringSign):
            return v.value

        assert False, f"expected string ref id or literal, got {v}"

    def step(self, state : State) -> Iterable[State | str]:
        assert isinstance(state, State), f"expected frame but got {state}"
        frame = state.frames.peek()
        opr = self.bc[frame.pc]
        logger.debug(f"STEP {opr}\n{state}")
        match opr:
            case jvm.Push(value=v):
                if v.type == jvm.Reference() and isinstance(v.value, str):
                    frame.stack.push(StringSign.abstract(v.value))
                frame.pc += 1
                yield state

            case jvm.Load(type=jvm.String(), index=i):
                frame.stack.push(frame.locals[i])
                frame.pc += 1
                yield state
                
            case jvm.Return(type=jvm.String()):
                state.frames.pop()
                if state.frames:
                    frame = state.frames.peek()
                    frame.pc += 1
                    yield state
                else:
                    yield "ok"
                    
            case jvm.Get(static=is_static, field=field):
                if "$assertionsDisabled" in str(field):
                    frame.stack.push("0")  # assertions are enabled
                    frame.pc += 1
                    yield state
            
            case jvm.New(classname=_cls):
                if str(_cls) == "java/lang/String":
                    obj_ref = state.next_ref
                    state.next_ref += 1
                    state.heap[obj_ref] = StringSign.abstract("")
                    frame.stack.push(state.heap[obj_ref])
                else:
                    frame.stack.push(jvm.Value.int(0))
                frame.stack.push(obj_ref)
                frame.pc += 1
                yield state

            case jvm.Dup():
                v = frame.stack.peek()
                frame.stack.push(v)
                frame.pc += 1
                yield state
            
            #todo: needs to be string
            case jvm.Store(type=jvm.String(), index=i):
                v = frame.stack.pop()
                frame.locals[i] = v
                frame.pc += 1
                yield state
            
            case jvm.Goto(target=t):
                frame.pc = PC(frame.pc.method, t)
                yield state
            
            case jvm.InvokeSpecial(method=mid):
                method_name = mid.extension.name
                if method_name == "<init>":
                    # Simulate object creation (same as jvm.New)
                    obj_ref = state.next_ref
                    state.next_ref += 1
                    state.heap[obj_ref] = StringSign.abstract("")
                    frame.stack.push(state.heap[obj_ref])
                    frame.pc += 1
                    yield state
                else:
                    # Handle other special methods
                    frame.pc += 1
                    yield state
                
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
                            
                            StringOperation.getLength(value)

                            frame.pc += 1
                            return state
                        case "concat":
                            arg = frame.stack.pop()
                            recv = frame.stack.pop()

                            value1 = self.get_stringSign(state, arg)
                            value2 = self.get_stringSign(state,recv)

                            frame.stack.push(
                                self.alloc_string_object(state, StringOperation.concat(value1,value2))
                            )
                            frame.pc += 1
                        case "equals":
                            arg = frame.stack.pop()
                            recv = frame.stack.pop()

                            value1 = self.get_stringSign(state, arg)
                            value2 = self.get_stringSign(state,recv)

                            result = StringOperation.equals(value1,value2)

                            if result == "assertion error":
                                is_equal = False

                            elif result == "maybe":
                                is_equal = False
                            
                            frame.stack.push(jvm.Value(jvm.Boolean(), is_equal))
                            frame.pc += 1

                        case "equalsIgnoreCase": # same as equals
                            arg = frame.stack.pop()
                            recv = frame.stack.pop()

                            value1 = self.get_stringSign(state, arg)
                            value2 = self.get_stringSign(state,recv)

                            result = StringOperation.equals(value1,value2)

                            if result == "assertion error":
                                is_equal = False

                            elif result == "maybe":
                                is_equal = False
                            
                            frame.stack.push(jvm.Value(jvm.Boolean(), is_equal))
                            frame.pc += 1

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

                            stringSign = self.get_stringSign(state,recv)

                            result = StringOperation.getChar(stringSign,i)

                            if isinstance(result,StringSign):
                                frame.stack.push(self.alloc_string_object(state,result))
                        
                            frame.pc += 1

                        case "substring":
                            end = frame.stack.pop()
                            start = frame.stack.pop()
                            recv = frame.stack.pop()

                            beginIndex, endIndex = start.value, end.value

                            assert isinstance(beginIndex, int) and isinstance(endIndex,int),f"expected int indices, got {start}, {end}"

                            stringSign = self.get_stringSign(state,recv)

                            StringOperation.subString(stringSign,beginIndex,endIndex)
                        case name:
                            raise NotImplementedError(
                                f"Don't know how to handle: {name}"
                            )
                else:  # not a string
                    frame.pc += 1
                    return state

            case jvm.Throw():
                yield "assertion error"
            
            case a:
                raise NotImplementedError(f"Don't know how to handle: {a!r}")
    
    def run_method(self,methodid: jvm.AbsMethodID,method_args: Tuple[jvm.Value, ...],max_steps: int = 1000) -> set[Union[State, str]]:
    
        frame = Frame.from_method(methodid)
    
        for i, v in enumerate(input.values):
            match v: 
                case jvm.Value(type=jvm.Int(), value = value):

                    assert isinstance(value,int)
                    jvm.Value(jvm.Reference(), value)
                    frame.locals[i] = v
                    
                case jvm.Value(type=jvm.Boolean(), value = value):

                    assert isinstance(value,bool)
                    jvm.Value(jvm.Reference(), value)
                    frame.locals[i] = v

                case jvm.Value(type=jvm.String(), value = value):
                    assert isinstance(value,str)
                    jvm.Value(jvm.Reference(), StringSign.abstract(value))
                    frame.locals[i] = v
                case _:
                    raise NotImplementedError(f"Don't know how to handle input value: {v!r}")

        results = set()
        worklist = deque([State({}, Stack.empty().push(frame))])

        while worklist and steps < max_steps:
            state = worklist.popleft()
            steps += 1

            out = self.step(state)

            for nxt in out:
                if isinstance(nxt, str):  # Terminated with result
                    results.add(nxt)
                else:
                    worklist.append(nxt)
        if steps >= max_steps:
            results.add("*")

        return results

def main():
# run: uv run solutions/abstract_string_interpreter.py --filter "Strings"

    suite = jpamb.Suite()

    methodid, input = jpamb.getcase()

    suite = jpamb.Suite()
    interpreter = Interpreter(suite)
    result = interpreter.run_method(methodid, input.values, 1000)

    print(result)

if __name__ == "__main__":
    main()
