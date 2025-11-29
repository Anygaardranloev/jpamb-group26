#!/usr/bin/env python3
"""
tree-sitter based syntactic analysis which extracts:
- int literals
- string literals
- char literals
- boolean usages
- comparison constants (var, op, val)
- numeric constants inside string manipulation
"""

import jpamb
import json
import tree_sitter
import tree_sitter_java

methodid = jpamb.getmethodid(
    "syntactic_analyzer",
    "0.1",
    "group26",
    ["syntactic", "python"],
    for_science=True
)

JAVA_LANGUAGE = tree_sitter.Language(tree_sitter_java.language())
parser = tree_sitter.Parser(JAVA_LANGUAGE)

class SyntacticAnalyzer:
    def __init__(self, methodid):
        self.methodid = methodid
        self.src = jpamb.sourcefile(methodid).read_text()
        self.tree = parser.parse(self.src.encode("utf8"))
        self.root = self.tree.root_node


    def treewalk(self, kind):
        stack = [self.root]
        while stack:
            node = stack.pop()
            if node.type == kind:
                yield node
            stack.extend(node.children)


    def text_of(self, node):
        return self.src[node.start_byte : node.end_byte]


    def get_int_lits(self):
        ints = []
        for n in self.treewalk("decimal_integer_literal"):
            ints.append(self.text_of(n))
        return sorted(set(ints))


    def get_str_lits(self):
        strs = []
        for n in self.treewalk("string_literal"):
            strs.append(self.text_of(n))
        return sorted(set(strs))


    def get_char_lits(self):
        chars = []
        for n in self.treewalk("character_literal"):
            lit = self.text_of(n)
            chars.append(lit.strip("'"))
        return sorted(set(chars))


    # still dont know if useful
    def get_uses_bool(self):
        for n in self.treewalk("boolean_literal"):
            return True
        return False


    def get_int_comps(self):
        comps = []
        for n in self.treewalk("binary_expression"):
            op = n.child_by_field_name("operator")
            if not op:
                continue
            op_text = self.text_of(op)

            if op_text not in {"==", "!=", "<=", ">=", "<", ">"}:
                continue

            left = n.child_by_field_name("left")
            right = n.child_by_field_name("right")
            if not left or not right:
                continue

            left_text = self.text_of(left)
            right_text = self.text_of(right)

            if left.type == "identifier" and right.type == "decimal_integer_literal":
                comps.append((left_text, op_text, right_text))
            if right.type == "identifier" and left.type == "decimal_integer_literal":
                comps.append((right_text, op_text, left_text))

        return sorted(set(comps))


    def get_str_method_consts(self):
        str_method_consts = []
        for n in self.treewalk("method_invocation"):
            name_n = n.child_by_field_name("name")
            if not name_n:
                continue
            name = self.text_of(name_n)
            if name not in {"substring", "charAt", "indexOf"}:
                continue

            args = n.child_by_field_name("arguments")
            if not args:
                continue
            for child in args.children:
                if child.type == "decimal_integer_literal":
                    str_method_consts.append(self.text_of(child))

        return sorted(set(str_method_consts))


    # returns set of triplets: (s.length(), op, int)
    def get_str_length_comps(self):
        comps = []
        for n in self.treewalk("binary_expression"):
            op = n.child_by_field_name("operator")
            if not op:
                continue
            op_text = self.text_of(op)
            if op_text not in {"==", "!=", "<=", ">=", "<", ">"}:
                continue

            left = n.child_by_field_name("left")
            right = n.child_by_field_name("right")
            if not left or not right:
                continue

            if left.type == "method_invocation":
                name = left.child_by_field_name("name")
                if name and self.text_of(name) == "length":
                    target = left.child_by_field_name("object")
                    if target and right.type == "decimal_integer_literal":
                        comps.append((self.text_of(target), op_text, self.text_of(right)))

            if right.type == "method_invocation":
                name = right.child_by_field_name("name")
                if name and self.text_of(name) == "length":
                    target = right.child_by_field_name("object")
                    if target and left.type == "decimal_integer_literal":
                        comps.append((self.text_of(target), op_text, self.text_of(left)))

        return sorted(set(comps))


    def get_regex_patterns(self):
        patterns = []
        for n in self.treewalk("method_invocation"):
            n_name = n.child_by_field_name("name")
            if not n_name:
                continue
            name = self.text_of(n_name)
            if name not in {"matches", "replaceAll", "split"}:
                continue

            args = n.child_by_field_name("arguments")
            if not args:
                continue

            for child in args.children:
                if child.type == "string_literal":
                    pattern = self.text_of(child).strip('"')
                    patterns.append((name, pattern))
                    break

        return patterns


    def get_all(self):
        return {
            "int_lits":             self.get_int_lits(),
            "str_lits":             self.get_str_lits(),
            "char_lits":            self.get_char_lits(),
            "uses_bool":            self.get_uses_bool(),
            "int_comps":            self.get_int_comps(),
            "str_method_consts":    self.get_str_method_consts(),
            "str_length_comps":     self.get_str_length_comps(),
            "regex_patterns":       self.get_regex_patterns(),
        }

analyzer = SyntacticAnalyzer(methodid)
print(analyzer.get_all())