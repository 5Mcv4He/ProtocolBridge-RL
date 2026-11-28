"""Single writer for a production directory; releases automatically on process exit.

The lock is execution coordination, not task admission or evidence validation.
It prevents two resumed controllers from both launching the same costly work.
"""
import contextlib
import fcntl
from pathlib import Path

@contextlib.contextmanager
def exclusive(directory):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.production.lock').open('a') as handle:
        try:
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another production controller owns this output directory')
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
