#!/usr/bin/env python3
"""
Syntactic analyzer, which checks for:
-
"""
import re

import jpamb
import json

methodid = jpamb.getmethodid(
    "syntactic_analyzer",
    "0.1",
    "group26",
    ["syntactic", "python"],
    for_science=True
)

src = jpamb.sourcefile(methodid).read_text()

int_literals = sorted(set(re.findall(r'\b(\d+)\b', src)))

string_literals = sorted(set(m.group(1) for m in re.finditer(r'"([^"\\]*(?:\\.[^"\\]*)*)"', src)))

char_literals = sorted(set(m.group(1) for m in re.finditer(r"'([^'\\]|\\.)'", src)))

# note: dont know if this is useful :p
uses_bool_literals = False
if "true" in src or "false" in src:
    uses_bool_literals = True

# store as triplet: (var, op, val)
comparison_ints = []
for m in re.finditer(r'(\w+)\s*(==|!=|<=|>=|<|>)\s*(\d+)', src):
    comparison_ints.append((m.group(1), m.group(2), m.group(3)))
for m in re.finditer(r'(\d+)\s*(==|!=|<=|>=|<|>)\s*(\w+)', src):
    comparison_ints.append((m.group(3), m.group(2), m.group(1)))

string_method_ints = []
for m in re.finditer(r'\b(substring|charAt|indexOf)\s*\(\s*(\d+)', src):
    string_method_ints.append(m.group(2))
string_method_ints = sorted(set(string_method_ints))

result = {
    "int_literals": int_literals,
    "string_literals": string_literals,
    "char_literals": char_literals,
    "uses_bool_literals": uses_bool_literals,
    "comparison_ints": comparison_ints,
}

print(json.dumps(result, ensure_ascii=False))