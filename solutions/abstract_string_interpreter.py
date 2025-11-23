import jpamb
from jpamb import jvm
from dataclasses import dataclass, field
from collections.abc import Iterable
from jpamb.jvm.base import Value
import unicodedata

import sys
from loguru import logger

from dataclasses import dataclass
from typing import Literal

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}")

Sign = Literal["letters", "numbers", "symbols"]
Encoding = Literal["latin1", "utf16"]

@dataclass
class SignSet:
    signs: set[Sign]
    encodings: set[Encoding]

    def __contains__(self, s: str) -> bool:
        """All chars in the string must match both sign and encoding."""
        for ch in s:
            if SignSet.sign_of_char(ch) not in self.signs:
                return False
            if SignSet.encoding_of_char(ch) not in self.encodings:
                return False
        return True

    @classmethod
    def abstract(cls, strings: set[str]) -> "SignSet":
        sign_set: set[Sign] = set()
        enc_set: set[Encoding] = set()

        for s in strings:
            for ch in s:
                sign_set.add(SignSet.sign_of_char(ch))
                enc_set.add(SignSet.encoding_of_char(ch))

        return cls(set(sign_set), set(enc_set))
    
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
    
    # Lattice ops
    def join(self, other: "SignSet") -> "SignSet":
        return SignSet(
            signs=self.signs | other.signs,
            encodings=self.encodings | other.encodings,
        )

    def meet(self, other: "SignSet") -> "SignSet":
        return SignSet(
            signs=self.signs & other.signs,
            encodings=self.encodings & other.encodings,
        )

    def is_leq(self, other: "SignSet") -> bool:
        return self.signs <= other.signs and self.encodings <= other.encodings

BOTTOM = SignSet(set(), set())
TOP = SignSet(
    set({"letters", "numbers", "symbols"}),
    set({"latin1", "utf16"})
)

if __name__ == "__main__":
    C = SignSet.abstract({"A3", "ø?", "🙂"})
    print(C)
