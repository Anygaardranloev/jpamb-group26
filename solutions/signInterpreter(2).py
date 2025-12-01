import jpamb
from jpamb import jvm
from dataclasses import dataclass, field
from collections.abc import Iterable
from jpamb.jvm.base import Value

import sys
from loguru import logger


from dataclasses import dataclass
from typing import TypeAlias, Literal

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}")


Sign : TypeAlias = Literal["+"] | Literal["-"] | Literal["0"] | Literal["true"] | Literal["false"]

@dataclass
class SignSet:
    signs : set[Sign]

    def __contains__(self, member : str) -> bool: 
        if (member in self.signs): 
            return True
        if (member in self.signs):
            return True
        if (member  in self.signs):
            return True
        return False
    
    def add(self, member : str) -> None:
        self.signs.add(member)


    @classmethod
    def abstract(cls, items : set[int]): 
        signset = set()
        if 0 in items:
            signset.add("0")
        if any(x > 0 for x in items):
            signset.add("+")
        if any(x < 0 for x in items):
            signset.add("-")
        return cls(signset)
    
class Arithmetic:

    def union(s1 : SignSet, s2 : SignSet) -> SignSet:
        return SignSet(s1.signs.union(s2.signs))
    
    def intersection(s1 : SignSet, s2 : SignSet) -> SignSet:
        return SignSet(s1.signs.intersection(s2.signs))

    @staticmethod
    def add(s1 : SignSet, s2 : SignSet) -> SignSet:
        result = set()
        if "+" in s1.signs or "+" in s2.signs:
            result.add("+")
        if "-" in s1.signs or "-" in s2.signs:
            result.add("-")
        if "0" in s1.signs and "0" in s2.signs:
            result.add("0")
        if ("+" in s1.signs and "-" in s2.signs) or ("-" in s1.signs and "+" in s2.signs):
            result.add("0")
        return SignSet(result)
    
    def subtract(s1 : SignSet, s2 : SignSet) -> SignSet:
        result = set()
        if "+" in s1.signs or "-" in s2.signs:
            result.add("+")
        if "-" in s1.signs or "+" in s2.signs:
            result.add("-")
        if "0" in s1.signs and "0" in s2.signs:
            result.add("0")
        if ("+" in s1.signs and "+" in s2.signs) or ("-" in s1.signs and "-" in s2.signs):
            result.add("0")
        return SignSet(result)
    
    def multiply(s1 : SignSet, s2 : SignSet) -> SignSet:
        result = set()
        if ("+" in s1.signs and "+" in s2.signs) or ("-" in s1.signs and "-" in s2.signs):
            result.add("+")
        if ("+" in s1.signs and "-" in s2.signs) or ("-" in s1.signs and "+" in s2.signs):
            result.add("-")
        if "0" in s1.signs or "0" in s2.signs:
            result.add("0")
        return SignSet(result)
    
    def divide(s1 : SignSet, s2 : SignSet) -> SignSet | str:
        result = set()
        if "0" in s2.signs:
            result.add("divide by zero")
        if "0" in s1.signs:
            result.add("0")
        if ("+" in s1.signs and "+" in s2.signs) or ("-" in s1.signs and "-" in s2.signs):
            result.add("+")
        if ("+" in s1.signs and "-" in s2.signs) or ("-" in s1.signs and "+" in s2.signs):
            result.add("-")
        return SignSet(result)
    
    def remainder(s1 : SignSet, s2 : SignSet) -> SignSet | str:
        result = set()
        if "0" in s2.signs:
            result.add("divide by zero")
        if "0" in s1.signs:
            result.add("0")
        if "+" in s1.signs:
            result.add("+")
        if "-" in s1.signs:
            result.add("-")
        return SignSet(result)
    
    def negate(s : SignSet) -> SignSet:
        result = set()
        if "+" in s.signs:
            result.add("-")
        if "-" in s.signs:
            result.add("+")
        if "0" in s.signs:
            result.add("0")
        return SignSet(result)
    
    def lessEqual(s1 : SignSet, s2 : SignSet) -> set[bool]:
        result = set()
        if ("-" in s1.signs and "+" in s2.signs) or ("-" in s1.signs and "0" in s2.signs) or ("0" in s1.signs and "+" in s2.signs) or ("0" in s1.signs and "0" in s2.signs):
            result.add(True)
        if ("+" in s1.signs and "-" in s2.signs) or ("+" in s1.signs and "0" in s2.signs) or ("0" in s1.signs and "-" in s2.signs):
            result.add(False)
        if ("+" in s1.signs and "+" in s2.signs) or ("-" in s1.signs and "-" in s2.signs):
            result.add(True)
            result.add(False)
        return result
    
    def greaterEqual(s1 : SignSet, s2 : SignSet) -> set[bool]:
        result = set()
        if ("-" in s1.signs and "+" in s2.signs) or ("-" in s1.signs and "0" in s2.signs) or ("0" in s1.signs and "+" in s2.signs):
            result.add(False)
        if ("+" in s1.signs and "-" in s2.signs) or ("+" in s1.signs and "0" in s2.signs) or ("0" in s1.signs and "-" in s2.signs) or ("0" in s1.signs and "0" in s2.signs):
            result.add(True)
        if ("+" in s1.signs and "+" in s2.signs) or ("-" in s1.signs and "-" in s2.signs):
            result.add(True)
            result.add(False)
        return result
    
    def lessThan(s1 : SignSet, s2 : SignSet) -> set[bool]:
        result = set()
        if ("-" in s1.signs and "+" in s2.signs) or ("-" in s1.signs and "0" in s2.signs) or ("0" in s1.signs and "+" in s2.signs):
            result.add(True)
        if ("+" in s1.signs and "-" in s2.signs) or ("+" in s1.signs and "0" in s2.signs) or ("0" in s1.signs and "-" in s2.signs) or ("0" in s1.signs and "0" in s2.signs):
            result.add(False)
        if ("+" in s1.signs and "+" in s2.signs) or ("-" in s1.signs and "-" in s2.signs):
            result.add(True)
            result.add(False)
        return result
    
    def greaterThan(s1 : SignSet, s2 : SignSet) -> set[bool]:
        result = set()
        if ("-" in s1.signs and "+" in s2.signs) or ("-" in s1.signs and "0" in s2.signs) or ("0" in s1.signs and "+" in s2.signs) or ("0" in s1.signs and "0" in s2.signs):
            result.add(False)
        if ("+" in s1.signs and "-" in s2.signs) or ("+" in s1.signs and "0" in s2.signs) or ("0" in s1.signs and "-" in s2.signs):
            result.add(True)
        if ("+" in s1.signs and "+" in s2.signs) or ("-" in s1.signs and "-" in s2.signs):
            result.add(True)
            result.add(False)
        return result
    
    def equal(s1 : SignSet, s2 : SignSet) -> set[bool]:
        result = set()
        if "0" in s1.signs and "0" in s2.signs:
            result.add(True)
        if ("+" in s1.signs and "+" in s2.signs) or ("-" in s1.signs and "-" in s2.signs):
            result.add(True)
            result.add(False)
        if ("+" in s1.signs and "-" in s2.signs) or ("-" in s1.signs and "+" in s2.signs) or ("0" in s1.signs and ("+" in s2.signs or "-" in s2.signs)) or (("+" in s1.signs or "-" in s1.signs) and "0" in s2.signs):
            result.add(False)
        return result
    
    def notEqual(s1 : SignSet, s2 : SignSet) -> set[bool]:
        result = set()
        if ("+" in s1.signs and "-" in s2.signs) or ("-" in s1.signs and "+" in s2.signs):
            result.add(True)
        if "0" in s1.signs and "0" in s2.signs:
            result.add(False)
        if ("+" in s1.signs and "+" in s2.signs) or ("-" in s1.signs and "-" in s2.signs):
            result.add(True)
            result.add(False)
        return result


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
    locals: dict[int, SignSet]
    stack: Stack[SignSet]
    pc: PC

    def __str__(self):
        locals = ", ".join(f"{k}:{v}" for k, v in sorted(self.locals.items()))
        return f"<{{{locals}}}, {self.stack}, {self.pc}>"

    def from_method(method: jvm.AbsMethodID) -> "Frame":
        return Frame({}, Stack.empty(), PC(method, 0))

import copy

@dataclass
class AState:
    heap: dict[int, jvm.Value]
    frames: Stack[Frame]

    def copy(self):
        return AState(copy.deepcopy(self.heap), copy.deepcopy(self.frames))

    def __str__(self):
        return f"{self.heap} {self.frames}"
    




def step(state : AState) -> Iterable[AState | str]:
    assert isinstance(state, AState), f"expected frame but got {state}"
    frame = state.frames.peek()
    opr = bc[frame.pc]
    # logger.debug(f"STEP {opr}\n{state}")
    match opr:
        case jvm.Push(value=v):
            if v.type == jvm.String():
                frame.stack.push(v)
            else:
                frame.stack.push(SignSet.abstract([v.value]))
            frame.pc += 1
            yield state

        case jvm.Load(type=jvm.Int(), index=i):
            frame.stack.push(frame.locals[i])
            frame.pc += 1
            yield state
        
        case jvm.Load(type=jvm.Float(), index=i):
            frame.stack.push(frame.locals[i])
            frame.pc += 1
            yield state

        case jvm.Load(type=jvm.Reference(), index=i):
            yield "String detected"
        
        case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Div): # Binary Division
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            result = Arithmetic.divide(v1, v2)
            if "divide by zero" in result:
                yield "divide by zero"
                result.signs.remove("divide by zero")
            # print(result)
            if result.signs.__len__() > 0:
                frame.stack.push(result)
                frame.pc += 1
                yield state
        
        case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Add): # Binary Division
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            result = Arithmetic.add(v1, v2)
            frame.stack.push(result)
            frame.pc += 1
            yield state
        
        case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Sub): # Binary Division
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            result = Arithmetic.subtract(v1, v2)
            frame.stack.push(result)
            frame.pc += 1
            yield state

        case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Mul): # Binary Division
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            result = Arithmetic.multiply(v1, v2)
            frame.stack.push(result)
            frame.pc += 1
            yield state
        

        case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Rem): # Binary Remainder
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            result = Arithmetic.remainder(v1, v2)
            frame.stack.push(result)
            frame.pc += 1
            yield state
        
        case jvm.Return(type=jvm.Int()):
            v1 = frame.stack.pop()
            state.frames.pop()
            if state.frames:
                frame = state.frames.peek()
                frame.stack.push(v1)
                frame.pc += 1
                yield state
            else:
                yield "ok"

        case jvm.Return(type=jvm.Reference()):
            v1 = frame.stack.pop()
            state.frames.pop()
            if state.frames:
                frame = state.frames.peek()
                frame.stack.push(v1)
                frame.pc += 1
                yield state
            else:
                if isinstance(v1.type, jvm.String):
                    yield v1.value
            
        case jvm.Return(type=None):
            state.frames.pop()
            if state.frames:
                frame = state.frames.peek()
                frame.pc += 1
                yield state
            else:
                yield "ok"

        case jvm.Ifz(condition=cond, target=val, offset = offset):
            currentPC = frame.pc
            v = frame.stack.pop()

            if "true" in v:
                frame.pc = PC(frame.pc.method, val)
                yield state.copy()
            if "false" in v:
                frame.pc = currentPC + 1
                yield state.copy()
      
            if cond == 'eq': 
                if "0" in v:
                    frame.pc = PC(frame.pc.method, val)
                    yield state.copy()
                if "+" in v or "-" in v:
                    frame.pc = currentPC + 1
                    yield state
            if cond == 'ne':
                if "+" in v or "-" in v:
                    frame.pc = PC(frame.pc.method, val)
                    yield state.copy()
                if "0" in v:
                    frame.pc = currentPC + 1
                    yield state
            if cond == 'gt': # greater than zero
                if "+" in v:
                    frame.pc = PC(frame.pc.method, val)
                    yield state.copy()
                if "0" in v or "-" in v:
                    frame.pc = currentPC + 1
                    yield state
            if cond == 'ge':
                if "0" in v or "+" in v:
                    frame.pc = PC(frame.pc.method, val)
                    yield state.copy()
                if "-" in v:
                    frame.pc = currentPC + 1
                    yield state
            if cond == 'le':
                if "0" in v or "-" in v:
                    frame.pc = PC(frame.pc.method, val)
                    yield state.copy()
                if "+" in v:
                    frame.pc = currentPC + 1
                    yield state
                

        case jvm.If(condition=cond, target=val):
            currentPC = frame.pc
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            if cond == 'gt': # greater than
                result = Arithmetic.greaterThan(v1, v2)
                if True in result:
                    frame.pc = PC(frame.pc.method, val)
                    yield state.copy()
                if False in result:
                    frame.pc = currentPC + 1
                    yield state
            if cond == 'ge': # greater than or equal
                result = Arithmetic.greaterEqual(v1, v2)
                if True in result:
                    frame.pc = PC(frame.pc.method, val)
                    yield state.copy()
                if False in result:
                    frame.pc = currentPC + 1
                    yield state
            if cond == 'ne': # not equal
                result = Arithmetic.notEqual(v1, v2)
                if True in result:
                    frame.pc = PC(frame.pc.method, val)
                    yield state.copy()
                if False in result:
                    frame.pc = currentPC + 1
                    yield state
            if cond == 'eq': # not equal
                result = Arithmetic.equal(v1, v2)
                if True in result:
                    frame.pc = PC(frame.pc.method, val)
                    yield state.copy()
                if False in result:
                    frame.pc = currentPC + 1
                    yield state
            if cond == 'lt': # less than
                result = Arithmetic.lessThan(v1, v2)
                if True in result:
                    frame.pc = PC(frame.pc.method, val)
                    yield state.copy()
                if False in result:
                    frame.pc = currentPC + 1
                    yield state
            if cond == 'le': # less than or equal
                result = Arithmetic.lessEqual(v1, v2)
                if True in result:
                    frame.pc = PC(frame.pc.method, val)
                    yield state.copy()
                if False in result:
                    frame.pc = currentPC + 1
                    yield state

        case jvm.CompareFloating(type=typ, nan_value=nan_val):
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            result = SignSet(set())
            # Compare the two float values
            if Arithmetic.greaterThan(v1, v2).__contains__(True):
                result.add("+")
            if Arithmetic.lessThan(v1, v2).__contains__(True):
                result.add("-")
            if Arithmetic.equal(v1, v2).__contains__(True):
                result.add("0")

            frame.stack.push(result)
            frame.pc += 1
            yield state

        case jvm.Get(static=is_static, field=field):
            if "$assertionsDisabled" in str(field):
                frame.stack.push("0")  # assertions are enabled
                frame.pc += 1
                yield state
        
        case jvm.New(classname=name):
            obj_ref = len(state.heap)
            state.heap[obj_ref] = {"class": name}
            frame.stack.push(obj_ref)
            frame.pc += 1
            yield state

        case jvm.Dup():
            v = frame.stack.peek()
            frame.stack.push(v)
            frame.pc += 1
            yield state
        
        case jvm.Store(type=jvm.Int(), index=i):
            v = frame.stack.pop()
            frame.locals[i] = v
            frame.pc += 1
            yield state
        
        case jvm.Goto(target=val):
            frame.pc = PC(frame.pc.method, val)
            yield state

        case jvm.Cast(from_=jvm.Int(), to_=jvm.Short()):
            frame.pc += 1
            yield state

        case jvm.Incr(index=i, amount=c):
            v = frame.locals[i]
            frame.locals[i] = Arithmetic.add(v, c)
            frame.pc += 1
            return state
        
        case jvm.InvokeSpecial(method=mid):
            method_name = mid.extension.name
            if method_name == "<init>":
                # Simulate object creation (same as jvm.New)
                obj_ref = len(state.heap)
                state.heap[obj_ref] = {"class": mid.classname._as_string}
                frame.stack.push(obj_ref)
                frame.pc += 1
                yield state
            else:
                # Handle other special methods
                frame.pc += 1
                yield state

        case jvm.InvokeStatic(method=mid):
            # logger.debug(f"InvokeStatic: classname={mid.classname.dotted()}, method={mid.extension.name}")

            params = getattr(mid.extension, "params", None)
            param_elems = getattr(params, "_elements", ()) if params is not None else ()
            param_count = len(param_elems)

            args = [frame.stack.pop() for _ in range(param_count)][::-1]

            callee = Frame.from_method(mid)
            for i, a in enumerate(args):
                callee.locals[i] = a

            state.frames.push(callee)
            yield state

        case jvm.NewArray():
            size = frame.stack.pop()
            if "0" in size or "-" in size:
                yield "negative array size"
            else:
                yield "Array found"

            
        case jvm.Throw():
            yield "assertion error"
        
        case a:
            raise NotImplementedError(f"Don't know how to handle: {a!r}")


from collections import deque
from typing import Iterable, Union
from jpamb import parse_input, parse_methodid

def run_all(initial: AState, max_steps: int = 1000) -> set[Union[AState, str]]:
    """Runs symbolic execution until all branches terminate or max_steps reached."""
    results = set()
    worklist = deque([initial])
    steps = 0

    while worklist and steps < max_steps:
        state = worklist.popleft()
        steps += 1

        out = step(state)

        for nxt in out:
            if isinstance(nxt, str):  # Terminated with result
                results.add(nxt)
            else:
                worklist.append(nxt)

    if steps >= max_steps:
        results.add("*")

    return results



suite = jpamb.Suite()
bc = Bytecode(suite, dict())
def run(method_id: str, input_str: str) -> None:

    methodid = parse_methodid(method_id)
    input = parse_input(input_str)

    frame = Frame.from_method(methodid)

    for i, v in enumerate(input.values):
        match v: 
            case jvm.Value(type=jvm.Int(), value = value):
                v = SignSet.abstract({value})
            case jvm.Value(type=jvm.Boolean(), value = value):
                v = SignSet("true" if value else "false")
            case jvm.Value(type=jvm.Float(), value = value):
                v = SignSet.abstract({int(value)})
            case jvm.Value(type=jvm.String(), value = value):
                v = SignSet(set())
                if "-" in value:
                    v.signs.add("-")
                if "+" in value:
                    v.signs.add("+")
                if "0" in value:
                    v.signs.add("0")
                # print(v)

            case _:
                raise NotImplementedError(f"Don't know how to handle input value: {v!r}")
        # print(f"Local {i} = {v}")
        frame.locals[i] = v


    initial_state = AState({}, Stack.empty().push(frame))
    results = run_all(initial_state)


    print(f"intput: {input_str} - {results}")

    return results

def main(argv=None):
    if argv is None:
        argv = sys.argv
    run(argv[1], argv[2])

if __name__ == "__main__":
    main(sys.argv)


# def many_step(state : dict[PC, AState | str]) -> dict[PC, AState | str]:
#   new_state = dict(state)
#   for k, v in state.items():
#       for s in step(v):
#         new_state[s.pc] |= s
#   return new_state