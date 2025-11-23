from dataclasses import dataclass, field
import unicodedata

import sys
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


if __name__ == "__main__":
    C = SignSet.abstract({"A3", "ø?", "🙂"})
    print(C)
