#!/usr/bin/env python3
"""Single-threaded exec shim: disable core dumps without threaded preexec_fn."""
import os
from pathlib import Path
import resource
import sys


def main():
    if len(sys.argv) != 3:
        raise ValueError("Expected absolute executable and model-directory paths")
    exe, model = map(Path, sys.argv[1:])
    if not exe.is_absolute() or not model.is_absolute() or not model.is_dir():
        raise ValueError("Executable and model directory must be absolute")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.execv(str(exe), [str(exe), str(model)])


if __name__ == "__main__":
    main()
