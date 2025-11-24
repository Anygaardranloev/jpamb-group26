#!/usr/bin/env python3
import argparse
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple, Tuple

from interpreter import PC, Interpreter
from loguru import logger

import jpamb
from jpamb import jvm
from collections import deque
import math
import random
import time

from jpamb.jvm.base import ClassName

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}")

# disable interpreter logging for fuzzing
logger.disable("interpreter")


@dataclass
class Coverage:
    bitmap: bytearray  # 8-bit counters (same size for global+per-run)
    last_loc: int = 0
    str_cmps: list = field(default_factory=list)

    def _loc_id(self, pc: "PC") -> int:
        # deterministic hash of (method, offset), truncated to bitmap size
        h = hash((str(pc.method), pc.offset))  # @TODO: Maybe fastter?
        return h & (len(self.bitmap) - 1)

    def hit_pc(self, pc: "PC"):
        loc = self._loc_id(pc)
        if self.bitmap[loc] < 0xFF:
            self.bitmap[loc] += 1
        self.last_loc = loc

    def reset(self):
        self.last_loc = 0
        self.bitmap[:] = b"\x00" * len(self.bitmap)
        self.str_cmps.clear()

    def score(self) -> int:
        # number of covered edges
        return sum(1 for b in self.bitmap if b)


@dataclass
class Testcase:
    input_values: list[jvm.Value] = field(default_factory=list)
    coverage_score: int = 0
    depth: int = 0


class Fuzzer:
    COVERAGE_SIZE = 1 << 10  # 1KB coverage bitmap

    def __init__(
        self,
        methodid: jvm.AbsMethodID,
        max_steps: int = 1000,
        max_iters: int = 1000,
        seed: int = 1337,
        max_corpus_size: int = 128,
    ):
        self.interpreter = Interpreter(
            jpamb.Suite(), Coverage(bytearray(self.COVERAGE_SIZE))
        )
        self.global_coverage = Coverage(bytearray(self.COVERAGE_SIZE))
        self.target_method = methodid
        self.target_method_params = [param for param in methodid.extension.params]
        logger.info(
            f"Fuzzing method: {self.target_method} with params {self.target_method_params}, seed={seed}"
        )
        self.max_steps = max_steps
        self.max_iters = max_iters
        self.corpus: deque[Testcase] = deque()
        self.random = random.Random(seed)
        self.max_corpus_size = max_corpus_size

    def generate_testcase(self) -> Testcase:
        input_values = []
        for param in self.target_method_params:
            match param:
                case jvm.Int():
                    val = self.random.randint(-100, 100)
                    input_values.append(jvm.Value(param, val))
                case jvm.Char():
                    val = chr(self.random.randint(32, 126))  # printable ASCII
                    input_values.append(jvm.Value(param, val))
                case jvm.Object(ClassName("java/lang/String")):
                    length = self.random.randint(0, 20)
                    s = "".join(
                        chr(self.random.randint(32, 126)) for _ in range(length)
                    )  # printable ASCII
                    input_values.append(jvm.Value(param, s))
                case _:
                    raise NotImplementedError(
                        f"Fuzzing for type {param} not implemented"
                    )

        return Testcase(input_values, 0)

    # def pick_parent(self) -> Testcase:
    #     """Pick a parent testcase from the corpus, weighted by coverage score."""
    #     if not self.corpus:
    #         return self.generate_testcase()

    #     weights = [1 + int(math.log2(tc.coverage_score + 1)) for tc in self.corpus]
    #     return self.random.choices(self.corpus, weights=weights, k=1)[0]

    def pick_parent(self) -> Testcase:
        """Pick a parent testcase from the corpus using an explore/exploit strategy."""
        if not self.corpus:
            return self.generate_testcase()

        max_score = max(tc.coverage_score for tc in self.corpus)

        best_candidates = [tc for tc in self.corpus if tc.coverage_score == max_score]
        best_parent = self.random.choice(best_candidates)

        if len(self.corpus) == 1 or self.random.random() < 0.7:
            return best_parent

        others = [tc for tc in self.corpus if tc.coverage_score < max_score]
        if not others:
            return best_parent

        return self.random.choice(others)

    def maybe_prune_corpus(self):
        if len(self.corpus) <= self.max_corpus_size:
            return

        # Sort by coverage_score descending, keep the best N
        sorted_corpus = sorted(
            self.corpus, key=lambda tc: tc.coverage_score, reverse=True
        )
        self.corpus = deque(sorted_corpus[: self.max_corpus_size])

    def mutate_value(self, val: jvm.Value) -> jvm.Value:
        match val.type:
            case jvm.Int():
                mutation = self.random.choice([-10, -1, 1, 10, 42, -42])
                new_val = val.value + mutation
                return jvm.Value(val.type, new_val)
            case jvm.Char():
                mutation = self.random.choice([-1, 1, 5, -5])
                new_val = chr(
                    max(32, min(126, ord(val.value) + mutation))
                )  # keep printable
                return jvm.Value(val.type, new_val)
            case jvm.Object(ClassName("java/lang/String")):
                s = val.value
                if len(s) == 0 or self.random.random() < 0.5:
                    # insert a character
                    pos = self.random.randint(0, len(s))
                    ch = chr(self.random.randint(32, 126))
                    new_s = s[:pos] + ch + s[pos:]
                else:
                    # modify a character
                    pos = self.random.randint(0, len(s) - 1)
                    ch = chr(self.random.randint(32, 126))
                    new_s = s[:pos] + ch + s[pos + 1 :]
                return jvm.Value(val.type, new_s)
            case _:
                raise NotImplementedError(
                    f"Mutation for type {val.type} not implemented"
                )

    def mutate_testcase(self, testcase: Testcase) -> Testcase:
        # start from a shallow copy of parent inputs
        new_vals = [jvm.Value(v.type, v.value) for v in testcase.input_values]

        # apply between 1 and N random mutations
        num_mutations = self.random.randint(1, 8)
        for _ in range(num_mutations):
            idx = self.random.randrange(len(new_vals))
            new_vals[idx] = self.mutate_value(new_vals[idx])

        return Testcase(
            input_values=new_vals,
            coverage_score=0,
            depth=testcase.depth + 1,
        )

    def run(self, max_iters: int = 1000) -> Tuple[str, int]:
        assert self.interpreter.coverage is not None
        # initial empty input

        # seed corpus with an initial testcase
        first = self.generate_testcase()
        self.corpus.append(first)

        best_score = 0
        for iteration in range(max_iters):
            if not self.corpus:
                # self.corpus.append(self.generate_testcase())
                logger.warning("Corpus is empty, fuzzing stopped.")
                break

            parent = self.pick_parent()
            testcase = self.mutate_testcase(parent)
            # logger.info(
            #     f"[{iteration:09}]: Running testcase with score {testcase.coverage_score} and inputs {testcase.input_values}, depth {testcase.depth}, corpus size {len(self.corpus)}"
            # )

            # Reset coverage for this run
            self.interpreter.coverage.reset()
            result = self.interpreter.run_method(
                self.target_method,
                tuple(testcase.input_values),
                max_steps=self.max_steps,
            )

            local_coverage = self.interpreter.coverage
            interesting = Fuzzer.is_interesting_run(
                local_coverage, self.global_coverage
            )

            if interesting:
                best_score = max(best_score, local_coverage.score())
                testcase.coverage_score = local_coverage.score()
                self.corpus.append(testcase)
                logger.info(
                    f"[{iteration}] new interesting testcase (score={testcase.coverage_score}): "
                    f"{testcase.input_values}, corpus size={len(self.corpus)}, depth={testcase.depth}"
                )
                self.maybe_prune_corpus()

            if result != "ok":
                logger.info(f"  Found interesting result: {result}")
                return result, best_score

        return "ok", best_score

    @staticmethod
    def is_interesting_run(local: Coverage, global_map: Coverage) -> bool:
        interesting = False
        for i, cnt in enumerate(local.bitmap):
            if cnt == 0:
                continue
            if global_map.bitmap[i] == 0:
                # completely new edge
                global_map.bitmap[i] = cnt
                interesting = True
            elif Fuzzer.bucket(cnt) > Fuzzer.bucket(global_map.bitmap[i]):
                # same edge, but more informative hitcount bucket
                global_map.bitmap[i] = cnt
                interesting = True
        return interesting

    @staticmethod
    def bucket(x: int) -> int:
        """AFL-style hitcount bucketing."""
        if x <= 0:
            return 0

        # thresholds for buckets 1..8
        thresholds = (1, 2, 4, 8, 16, 32, 128)

        for idx, t in enumerate(thresholds, start=1):
            if x <= t:
                return idx
        return len(thresholds) + 1


def main():
    example = """Example usage:
    uv run solutions/fuzzer.py "jpamb.cases.Strings.hardPassphrase:(Ljava/lang/String;)V"
"""

    ap = argparse.ArgumentParser(
        epilog=example, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("methodid", type=str, help="Method ID to execute")
    ap.add_argument(
        "--max-steps", type=int, default=1000, help="Maximum number of steps per run"
    )
    ap.add_argument(
        "--max-iters",
        type=int,
        default=100000000,
        help="Maximum number of fuzzing iterations",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=time.time_ns(),
        help="Random seed for reproducibility",
    )
    args = ap.parse_args()

    try:
        methodid = jvm.AbsMethodID.decode(args.methodid)
    except Exception as e:
        logger.error(f"Failed to decode method ID: {e}")
        return

    fuzzer = Fuzzer(
        methodid, max_steps=args.max_steps, max_iters=args.max_iters, seed=args.seed
    )
    result, coverage = fuzzer.run(max_iters=args.max_iters)

    print(f"Fuzzing finished with result: {result}, coverage score: {coverage}")


if __name__ == "__main__":
    main()
