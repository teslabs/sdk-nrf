"""
External content
################

Copyright (c) 2021 Nordic Semiconductor ASA
SPDX-License-Identifier: Apache-2.0

Introduction
============

This extension allows to import sources from directories out of the Sphinx
source directory. They are copied to the source directory before starting the
build. Note that the copy is *smart*, that is, only updated files are actually
copied. Therefore, incremental builds detect changes correctly and behave as
expected.

Paths for external content ingluded via e.g. figure, literalinclude, etc.
are adjusted as needed.

Configuration options
=====================

- ``external_content_contents``: A list of external contents. Each entry is
  a tuple with two fields: the external base directory and a file glob pattern.
- ``external_content_directives``: A list of directives that should be analyzed
  and their paths adjusted if necessary. Defaults to ``DEFAULT_DIRECTIVES``.
"""

from distutils.file_util import copy_file
import os
from pathlib import Path
import re
from typing import Dict, Any, List

from sphinx.application import Sphinx


__version__ = "0.1.0"


DEFAULT_DIRECTIVES = ("figure", "image", "include", "literalinclude")
"""Default directives for included content."""


def adjust_includes(
    fname: Path, basepath: Path, directives: List[str], encoding: str
) -> None:
    """Adjust included content paths.

    Args:
        fname: File to be processed.
        basepath: Base path to be used to resolve content location.
        directives: Directives to be parsed and adjusted.
        encoding: Sources encoding.
    """

    if fname.suffix != ".rst":
        return

    def _adjust(m):
        directive, fpath = m.groups()

        # ignore absolute paths or existing files
        if fpath.startswith("/") or (fname.parent / fpath).exists():
            fpath_adj = fpath
        else:
            fpath_adj = Path(os.path.relpath(basepath / fpath, fname.parent)).as_posix()

        return f".. {directive}:: {fpath_adj}"

    with open(fname, "r+", encoding=encoding) as f:
        content = f.read()
        content_adj, modified = re.subn(
            r"\.\. (" + "|".join(directives) + r")::\s*([^`\n]+)", _adjust, content
        )
        if modified:
            f.seek(0)
            f.write(content_adj)
            f.truncate()


def sync_contents(app: Sphinx) -> None:
    """Synhronize external contents.

    Args:
        app: Sphinx application instance.
    """

    srcdir = Path(app.srcdir)
    to_copy = []

    for content in app.config.external_content_contents:
        prefix_src, glob = content
        for src in prefix_src.glob(glob):
            if src.is_dir():
                to_copy.extend(
                    [(f, prefix_src) for f in src.glob("**/*") if not f.is_dir()]
                )
            else:
                to_copy.append((src, prefix_src))

    for entry in to_copy:
        src, prefix_src = entry
        dst = srcdir / src.relative_to(prefix_src)

        if not dst.parent.exists():
            dst.parent.mkdir(parents=True)

        status = copy_file(str(src), str(dst), update=True)
        if status[1]:
            adjust_includes(
                dst,
                src.parent,
                app.config.external_content_directives,
                app.config.source_encoding,
            )


def setup(app: Sphinx) -> Dict[str, Any]:
    app.add_config_value("external_content_contents", [], "env")
    app.add_config_value("external_content_directives", DEFAULT_DIRECTIVES, "env")

    app.connect("builder-inited", sync_contents)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
