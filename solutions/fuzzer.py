#!/usr/bin/env python3
import argparse
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple, Tuple, List

from interpreter import PC, Interpreter
from loguru import logger

import jpamb
from jpamb import jvm
from collections import deque
import math
import random
import time
import signal

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
    stagnant_execs: int = 0


class Fuzzer:
    COVERAGE_SIZE = 1 << 10  # 1KB coverage bitmap
    STAGNANT_ITER_LIMIT = 350_000
    STAGNANT_CHANGE_STRATEGY = 100_000
    USELESS_TESTCASE_ITER_LIMIT = 120_000

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
        self.crashes: List[Testcase] = []
        # keep a set of crash signatures so we only store unique crashes
        self._crash_signatures: set[tuple] = set()
        self._stop_requested = False
        self.stagnant_iters = 0

        # install Ctrl-C handler to gracefully stop fuzzing
        signal.signal(signal.SIGINT, self._handle_sigint)

    def _handle_sigint(self, _signum, _frame):  # type: ignore[override]
        logger.warning("Ctrl-C received, stopping fuzzing after current iteration...")
        self._stop_requested = True

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
                    length = self.random.randint(0, 30)
                    s = "".join(
                        chr(self.random.randint(32, 126)) for _ in range(length)
                    )  # printable ASCII
                    input_values.append(jvm.Value(param, s))
                case _:
                    raise NotImplementedError(
                        f"Fuzzing for type {param} not implemented"
                    )

        return Testcase(input_values, 0)

    def pick_parent_uniform(self) -> Testcase:
        """Pick a parent testcase from the corpus uniformly among the worse 80%.

        We define the worse 80% as those testcases with coverage score below the
        20th percentile. This strategy encourages exploration of less-covered paths, if we could not find new coverage recently using exploitative strategies.
        """
        if not self.corpus:
            return self.generate_testcase()

        score_threshold = sorted(tc.coverage_score for tc in self.corpus)[
            max(1, len(self.corpus) // 5) - 1
        ]  # top 20%
        filtered_candidates = [
            tc for tc in self.corpus if tc.coverage_score < score_threshold
        ]

        if not filtered_candidates:
            filtered_candidates = self.corpus

        return self.random.choice(filtered_candidates)

    def pick_parent_exploit(self) -> Testcase:
        """Pick a parent testcase from the corpus using an explore/exploit strategy."""
        if not self.corpus:
            return self.generate_testcase()

        score_threshold = sorted(tc.coverage_score for tc in self.corpus)[
            max(1, len(self.corpus) // 5) - 1
        ]  # top 20%
        best_candidates = [
            tc for tc in self.corpus if tc.coverage_score >= score_threshold
        ]
        best_parent = self.random.choice(best_candidates)

        if len(self.corpus) == 1 or self.random.random() < 0.7:
            return best_parent

        others = [tc for tc in self.corpus if tc.coverage_score < score_threshold]
        if not others:
            return best_parent

        return self.random.choice(others)

    def schedule_testcase(self) -> Testcase:
        if self.stagnant_iters <= Fuzzer.STAGNANT_CHANGE_STRATEGY:
            testcase = self.pick_parent_exploit()
        else:
            testcase = self.pick_parent_uniform()

        return testcase

    def maybe_prune_corpus(self):
        # 1. Remove useless testcases (nothing interesting was derived from them for a long time)
        for tc in list(self.corpus):
            if tc.stagnant_execs > Fuzzer.USELESS_TESTCASE_ITER_LIMIT:
                self.corpus.remove(tc)

        if len(self.corpus) <= self.max_corpus_size:
            return

        # Sort by coverage_score descending, keep the best N
        sorted_corpus = sorted(
            self.corpus, key=lambda tc: tc.coverage_score, reverse=True
        )
        self.corpus = deque(sorted_corpus[: self.max_corpus_size])

    def mutate_int(self, val: int) -> jvm.Value:
        mutation = self.random.choice([-10, -1, 1, 10, 42, -42])
        new_val = val + mutation
        return jvm.Value(jvm.Int(), new_val)

    def mutate_char(self, val: str) -> jvm.Value:
        mutation = self.random.choice([-1, 1, 5, -5])
        new_val = chr(max(32, min(126, ord(val) + mutation)))  # keep printable
        return jvm.Value(jvm.Char(), new_val)

    def mutate_string(self, s: str) -> jvm.Value:
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
        return jvm.Value(jvm.Object(ClassName("java/lang/String")), new_s)

    def mutate_value(self, val: jvm.Value) -> jvm.Value:
        match val.type:
            case jvm.Int():
                return self.mutate_int(val.value)
            case jvm.Char():
                return self.mutate_char(val.value)
            case jvm.Object(ClassName("java/lang/String")):
                return self.mutate_string(val.value)
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

    def run(self, max_iters: int = 1000) -> int:
        assert self.interpreter.coverage is not None
        # initial empty input

        # seed corpus with an initial testcase
        first = self.generate_testcase()
        self.corpus.append(first)

        best_score = 0
        # counter for consecutive iterations without new coverage
        for iteration in range(max_iters):
            if self._stop_requested:
                logger.info("Stop requested, terminating fuzzing loop.")
                break

            parent = self.schedule_testcase()
            testcase = self.mutate_testcase(parent)

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
                    f"[{iteration:9}] new interesting testcase (score={testcase.coverage_score}): "
                    f"{testcase.input_values}, depth={testcase.depth}, corpus size={len(self.corpus)}, crashes={len(self.crashes)}"
                )
                self.stagnant_iters = 0
                parent.stagnant_execs = 0
            else:
                parent.stagnant_execs += 1
                self.stagnant_iters += 1

            self.maybe_prune_corpus()

            if result != "ok":
                # build a hashable signature of the crash based on result and inputs
                sig = (
                    result,
                    tuple((str(v.type), v.value) for v in testcase.input_values),
                )
                if sig not in self._crash_signatures:
                    self._crash_signatures.add(sig)
                    self.crashes.append(testcase)
                    logger.warning(
                        f"Found interesting result: {result}, for inputs {testcase.input_values}"
                    )

            # stop if no new coverage has been produced for a long time
            if self.stagnant_iters >= Fuzzer.STAGNANT_ITER_LIMIT:
                logger.info(
                    f"Stopping fuzzing due to {Fuzzer.STAGNANT_ITER_LIMIT} iterations without new coverage."
                )
                break

        return self.global_coverage.score()

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
        default=100_000_000,
        help="Maximum number of fuzzing iterations",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=time.time_ns(),
        help="Random seed for reproducibility",
    )
    ap.add_argument(
        "--max-corpus-size",
        type=int,
        default=128,
        help="Maximum size of the corpus",
    )
    args = ap.parse_args()

    try:
        methodid = jvm.AbsMethodID.decode(args.methodid)
    except Exception as e:
        logger.error(f"Failed to decode method ID: {e}")
        return

    fuzzer = Fuzzer(
        methodid,
        max_steps=args.max_steps,
        max_iters=args.max_iters,
        seed=args.seed,
        max_corpus_size=args.max_corpus_size,
    )
    coverage = fuzzer.run(max_iters=args.max_iters)

    print(f"Fuzzing finished with coverage score: {coverage}")

    if fuzzer.crashes:
        print("\n=== Crashes collected during this session ===")
        for idx, tc in enumerate(fuzzer.crashes, start=1):
            print(
                f"Crash #{idx} inputs: {tc.input_values}, depth={tc.depth}, score={tc.coverage_score}"
            )


if __name__ == "__main__":
    main()
