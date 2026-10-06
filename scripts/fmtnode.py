#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "jsonfold",
# ]
# ///
from __future__ import annotations

import json
import textwrap
from argparse import ArgumentParser
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

import jsonfold

META_FILES = (
    "zarr.json",
    ".zgroup",
    ".zarray",
    ".zattrs",
)


def list_files(p: Path) -> Iterable[Path]:
    for root, _dirs, files in p.walk():
        for f in files:
            yield root / f


@dataclass(order=True)
class NodeResult:
    path: Path
    metadata: dict[str, Any]
    """Map from metadata file name to parsed JSON contents."""
    non_node_children: list[Path]
    child_nodes: Sequence[NodeResult]

    @classmethod
    def read(cls, path: Path) -> Self:
        if not path.is_dir():
            raise NotADirectoryError(str(path))
        metadata = {}
        non_node_children = []
        to_descend: list[Path] = []

        for sub in path.iterdir():
            if sub.is_dir():
                to_descend.append(sub)
            elif sub.is_file():
                if sub.name in META_FILES:
                    metadata[sub.name] = json.loads(sub.read_text())
                else:
                    non_node_children.append(sub)

        children_to_parse = []
        for item in to_descend:
            is_node = False
            for m in META_FILES:
                if item.joinpath(m).is_file():
                    is_node = True
                    children_to_parse.append(item)
                    break
            if not is_node:
                non_node_children.extend(list_files(item))
        child_nodes = [cls.read(p) for p in children_to_parse]
        return cls(path, metadata, non_node_children, child_nodes)

    def to_str(
        self, relative_to: Path | None = None, indent=" " * 4, initial_level=0
    ) -> str:
        if relative_to is None:
            path = self.path
        else:
            path = self.path.relative_to(relative_to)
        common_indent = indent * initial_level
        lines = [f"{common_indent}{path}/"]
        lines.append(
            f"{common_indent}{indent}Non-node descendant files: {len(self.non_node_children)}"
        )
        for m in META_FILES:
            val = self.metadata.get(m)
            if val is None:
                continue
            lines.append(f"{common_indent}{indent}{m}")
            content = jsonfold.dumps(self.metadata[m]).rstrip()
            lines.append(textwrap.indent(content, common_indent + indent * 2))

        for child in sorted(self.child_nodes):
            lines.append(child.to_str(self.path, indent, initial_level + 1))

        return "\n".join(lines)


def main(raw: Sequence[str] | None = None):
    parser = ArgumentParser()
    parser.add_argument("path", nargs="+", type=Path)
    args = parser.parse_args(raw)
    for p in args.path:
        res = NodeResult.read(p)
        print(res.to_str())


if __name__ == "__main__":
    main()
