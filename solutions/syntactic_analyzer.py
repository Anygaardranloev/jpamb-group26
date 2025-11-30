#!/usr/bin/env python3
"""Tree-sitter based syntactic analysis that extracts literals for fuzzing.

This script is meant to be called by ``jpamb`` in the same way as the
provided ``syntaxer.py`` solution, but instead of predicting properties of the
method under test it outputs a JSON object with the literals that appear in
that method. A later fuzzing stage can then read this JSON and use the
discovered values as mutation seeds.
"""

import argparse
import json

import jpamb
import tree_sitter
import tree_sitter_java

JAVA_LANGUAGE = tree_sitter.Language(tree_sitter_java.language())
PARSER = tree_sitter.Parser(JAVA_LANGUAGE)


class LiteralExtractor:
    """Extract integer and string related literals from a single method.

    The extractor focuses on data that is directly useful for input
    generation:

    - integer literals used anywhere in the body
    - character literals
    - string literals
    - integer literals that occur as arguments to common string methods
      (``substring``, ``charAt``, ``indexOf``), which often encode
      boundary-related information
    """

    def __init__(self, methodid: "jpamb.jvm.AbsMethodID") -> None:
        self.methodid = methodid
        src_path = jpamb.sourcefile(methodid)
        self.src = src_path.read_text(encoding="utf8")
        self.tree = PARSER.parse(self.src.encode("utf8"))
        self.root = self.tree.root_node

        # Restrict all analysis to the specific method body we are asked
        # about. This mirrors the logic used in ``solutions/syntaxer.py``.
        self._method_body = self._find_method_body()

    # --- AST location helpers -----------------------------------------

    def _find_class_node(self):
        """Locate the class node matching the method's declaring class.

        Uses a simple tree walk (no QueryCursor) to stay compatible with the
        Python Tree-sitter bindings.
        """

        simple_classname = str(self.methodid.classname.name)

        def walk(node):
            if node.type == "class_declaration":
                name_child = None
                for child in node.children:
                    if child.type == "identifier":
                        name_child = child
                        break
                if name_child and self._text(name_child) == simple_classname:
                    return node
            for child in node.children:
                found = walk(child)
                if found is not None:
                    return found
            return None

        return walk(self.root)

    def _find_method_body(self):
        """Locate the body node of the specific method under test."""

        class_node = self._find_class_node()
        if class_node is None:
            return None

        method_name = self.methodid.extension.name

        def walk(node):
            if node.type == "method_declaration":
                name_child = None
                for child in node.children:
                    if child.type == "identifier":
                        name_child = child
                        break
                if name_child and self._text(name_child) == method_name:
                    return node.child_by_field_name("body")
            for child in node.children:
                found = walk(child)
                if found is not None:
                    return found
            return None

        return walk(class_node)

    # --- small helpers -------------------------------------------------

    def _walk(self, kind: str):
        # If we failed to locate the method body (should not normally
        # happen), fall back to walking the whole tree.
        start_node = self._method_body or self.root
        stack = [start_node]
        while stack:
            node = stack.pop()
            if node.type == kind:
                yield node
            stack.extend(node.children)

    def _text(self, node) -> str:
        return self.src[node.start_byte : node.end_byte]

    # --- literal extraction --------------------------------------------

    def int_literals(self):
        values = []
        # Tree-sitter Java uses different node types for numeric literals,
        # e.g. "decimal_integer_literal" and "hex_integer_literal".
        for node in self._walk("decimal_integer_literal"):
            text = self._text(node)
            try:
                values.append(int(text, 10))
            except ValueError:
                # Fall back to keeping the raw text if parsing fails.
                continue

        for node in self._walk("hex_integer_literal"):
            text = self._text(node)
            try:
                values.append(int(text, 16))
            except ValueError:
                continue

        # Return unique, sorted integers.
        return sorted(set(values))

    def char_literals(self):
        values = []
        for node in self._walk("character_literal"):
            lit = self._text(node)
            # remove surrounding single quotes, keep escape sequences
            if lit.startswith("'") and lit.endswith("'") and len(lit) >= 2:
                lit = lit[1:-1]
            values.append(lit)
        return sorted(set(values))

    def string_literals(self):
        values = []
        for node in self._walk("string_literal"):
            lit = self._text(node)
            # remove surrounding double quotes, keep the raw Java content
            if lit.startswith('"') and lit.endswith('"') and len(lit) >= 2:
                lit = lit[1:-1]
            values.append(lit)
        return sorted(set(values))

    def string_index_constants(self):
        """Integer literals used as indices in string methods.

        Returns a sorted list of the *string* representation of the literal
        values (e.g. ["0", "1", "2"]). These are especially useful for
        boundary mutations of string inputs.
        """

        consts = []
        for node in self._walk("method_invocation"):
            name_node = node.child_by_field_name("name")
            if not name_node:
                continue
            name = self._text(name_node)
            if name not in {"substring", "charAt", "indexOf"}:
                continue

            args = node.child_by_field_name("arguments")
            if not args:
                continue
            for child in args.children:
                if child.type == "decimal_integer_literal":
                    consts.append(self._text(child))

        return sorted(set(consts))

    def to_json(self) -> str:
        """Return a JSON string with all extracted literals.

        The structure is intentionally simple so that a fuzzer can load it
        without depending on ``jpamb``:

        ::

            {
              "int_literals": ["0", "1", ...],
              "char_literals": ["a", "b", ...],
              "string_literals": ["foo", "bar", ...],
              "string_index_constants": ["0", "1", ...]
            }
        """

        data = {
            "int_literals": self.int_literals(),
            "char_literals": self.char_literals(),
            "string_literals": self.string_literals(),
            "string_index_constants": self.string_index_constants(),
        }
        return json.dumps(data, indent=4, sort_keys=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract integer and string related literals from a Java method "
            "using tree-sitter."
        )
    )
    parser.add_argument(
        "methodid",
        type=str,
        help=(
            "The method ID to analyze, or 'info' to print metadata " "about this tool."
        ),
    )
    args = parser.parse_args()

    if args.methodid == "info":
        # Let jpamb know about this analysis tool
        jpamb.printinfo(
            "syntactic_analyzer",
            "0.2",
            "group26",
            ["syntactic", "python"],
            for_science=True,
        )
        return

    try:
        methodid = jpamb.jvm.AbsMethodID.decode(args.methodid)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Error: Invalid method ID '{args.methodid}': {exc}")
        return

    extractor = LiteralExtractor(methodid)
    print(extractor.to_json())


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
