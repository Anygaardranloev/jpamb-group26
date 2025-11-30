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

    def _loc_id(self, pc: "PC") -> int:
        # deterministic hash of (method, offset), truncated to bitmap size
        h = hash((str(pc.method), pc.offset))  # @TODO: Maybe fastter?
        return h & (len(self.bitmap) - 1)

    def hit_loc(self, loc: int):
        if self.bitmap[loc] < 0xFF:
            self.bitmap[loc] += 1
        self.last_loc = loc

    def hit_pc(self, pc: "PC"):
        loc = self._loc_id(pc)
        self.hit_loc(loc)

    def log_int32_cmp(self, pc: "PC", val1: int, val2: int):
        loc = self._loc_id(pc)

        sign = (val1 < 0 == val2 < 0) or (val1 >= 0 and val2 >= 0)
        if sign:
            self.hit_loc(loc + 4)

            byte0 = (val1 & (0xFF << 24)) == (val2 & (0xFF << 24))
            if byte0:
                self.hit_loc(loc + 1)

                byte1 = (val1 & (0xFF << 16)) == (val2 & (0xFF << 16))
                if byte1:
                    self.hit_loc(loc + 2)

                    byte2 = (val1 & (0xFF << 8)) == (val2 & (0xFF << 8))
                    if byte2:
                        self.hit_loc(loc + 3)

    def log_str_cmp(self, pc: "PC", val1: str, val2: str, case_sensitive: bool = True):
        if not case_sensitive:
            val1 = val1.lower()
            val2 = val2.lower()

        loc = self._loc_id(pc)

        min_len = min(len(val1), len(val2))
        if min_len == 0:
            return

        # Check character by character
        for i in range(min_len):
            if val1[i] == val2[i]:
                self.hit_loc(loc + 1 + i)
            else:
                break

    def reset(self):
        self.last_loc = 0
        self.bitmap[:] = b"\x00" * len(self.bitmap)

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
        use_syntactic_analysis: bool = False,
    ):
        self.interpreter = Interpreter(
            jpamb.Suite(), Coverage(bytearray(self.COVERAGE_SIZE))
        )
        self.global_coverage = Coverage(bytearray(self.COVERAGE_SIZE))
        self.target_method = methodid
        self.target_method_params = [param for param in methodid.extension.params]
        logger.info(
            f"Fuzzing method: {self.target_method} with params {self.target_method_params}, seed={seed}, use_syntactic_analysis={use_syntactic_analysis}"
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

    def generate_int(self) -> jvm.Value:
        val = self.random.randint(-100, 100)
        return jvm.Value(jvm.Int(), val)

    def generate_char(self) -> jvm.Value:
        val = chr(self.random.randint(32, 126))  # printable ASCII
        return jvm.Value(jvm.Char(), val)

    def generate_array(
        self, elem_type: jvm.Type, length: int, return_as_string: bool = False
    ) -> jvm.Value:
        array_vals = []
        for _ in range(length):
            match elem_type:
                case jvm.Int():
                    array_vals.append(self.generate_int().value)
                case jvm.Char():
                    array_vals.append(self.generate_char().value)
                case _:
                    raise NotImplementedError(
                        f"Fuzzing for array element type {elem_type} not implemented"
                    )
        if return_as_string and isinstance(elem_type, jvm.Char):
            s = "".join(array_vals)
            return jvm.Value(jvm.Object(ClassName("java/lang/String")), s)
        else:
            return jvm.Value(jvm.Array(elem_type), array_vals)

    def generate_testcase(self) -> Testcase:
        input_values = []
        for param in self.target_method_params:
            match param:
                case jvm.Int():
                    val = self.generate_int()
                case jvm.Char():
                    val = self.generate_char()
                case jvm.Object(ClassName("java/lang/String")):
                    length = self.random.randint(0, 30)
                    val = self.generate_array(jvm.Char(), length, return_as_string=True)
                case jvm.Array(elem_type):
                    length = self.random.randint(0, 20)
                    val = self.generate_array(elem_type, length)
                case _:
                    raise NotImplementedError(
                        f"Testcase generation for param type {param} not implemented"
                    )
            input_values.append(val)

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

    def mutate_int(self, val: int) -> jvm.Value:
        if random.random() < 0.2:
            mutation = self.random.choice([-10, -1, 1, 10, 42, -42])
            new_val = val + mutation
        elif random.random() < 0.8:
            random_byte = self.random.randint(0, 255)
            random_shift = self.random.choice([0, 8, 16, 24])
            new_val = (val & ~(0xFF << random_shift)) | (random_byte << random_shift)
        else:  # change sign
            new_val = -val

        return jvm.Value(jvm.Int(), new_val)

    def mutate_char(self, val: str) -> jvm.Value:
        mutation = self.random.choice([-1, 1, 5, -5])
        new_val = chr(max(32, min(126, ord(val) + mutation)))  # keep printable
        return jvm.Value(jvm.Char(), new_val)

    def mutate_string(self, s: str) -> jvm.Value:
        if len(s) == 0 or self.random.random() < 0.3:
            # insert a character
            pos = self.random.randint(0, len(s))
            ch = chr(self.random.randint(32, 126))
            new_s = s[:pos] + ch + s[pos:]
        elif self.random.random() < 0.9:
            # modify a character
            pos = self.random.randint(0, len(s) - 1)
            ch = chr(self.random.randint(32, 126))
            new_s = s[:pos] + ch + s[pos + 1 :]
        else:
            # delete a character
            pos = self.random.randint(0, len(s) - 1)
            new_s = s[:pos] + s[pos + 1 :]
        return jvm.Value(jvm.Object(ClassName("java/lang/String")), new_s)

    def mutate_array(self, arr: list, elem_type: jvm.Type) -> jvm.Value:
        if len(arr) == 0 or self.random.random() < 0.5:
            # insert an element
            pos = self.random.randint(0, len(arr))
            match elem_type:
                case jvm.Int():
                    new_elem = self.generate_int().value
                case jvm.Char():
                    new_elem = self.generate_char().value
                case _:
                    raise NotImplementedError(
                        f"Mutation for array element type {elem_type} not implemented"
                    )
            new_arr = arr[:pos] + [new_elem] + arr[pos:]
        else:
            # modify an element
            pos = self.random.randint(0, len(arr) - 1)
            match elem_type:
                case jvm.Int():
                    new_elem = self.mutate_int(arr[pos]).value
                case jvm.Char():
                    new_elem = self.mutate_char(arr[pos]).value
                case _:
                    raise NotImplementedError(
                        f"Mutation for array element type {elem_type} not implemented"
                    )
            new_arr = arr[:pos] + [new_elem] + arr[pos + 1 :]
        return jvm.Value(jvm.Array(elem_type), new_arr)

    def mutate_value(self, val: jvm.Value) -> jvm.Value:
        match val.type:
            case jvm.Int():
                return self.mutate_int(val.value)
            case jvm.Char():
                return self.mutate_char(val.value)
            case jvm.Object(ClassName("java/lang/String")):
                return self.mutate_string(val.value)
            case jvm.Array(elem_type):
                return self.mutate_array(val.value, elem_type)
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
            testcase.coverage_score = local_coverage.score()

            if interesting:
                best_score = max(best_score, local_coverage.score())
                self.corpus.append(testcase)
                logger.info(
                    f"[{iteration:9}] new interesting testcase (score={testcase.coverage_score}): "
                    f"{testcase.input_values}, depth={testcase.depth}, corpus size={len(self.corpus)}, crashes={len(self.crashes)}"
                )
                self.stagnant_iters = 0
            else:
                self.stagnant_iters += 1

            if result != "ok":
                # Build a hashable signature of the crash based on result and coverage.
                # We're not including input values in the signature to avoid generating
                # too many "unique" crashes that differ only in input but not in behavior.
                sig = (
                    result,
                    hash(tuple(local_coverage.bitmap)),
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
    ap.add_argument(
        "--use-syntactic-analysis",
        type=bool,
        default=False,
        help="Whether to use syntactic analysis to guide fuzzing (1 = yes, 0 = no)",
    )
    args = ap.parse_args()

    if args.methodid == "info":
        jpamb.printinfo(
            "fuzzer",
            "0.1",
            "group26",
            ["fuzzer", "python"],
            for_science=True,
        )

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
        use_syntactic_analysis=args.use_syntactic_analysis,
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
