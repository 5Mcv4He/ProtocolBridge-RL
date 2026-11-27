"""Conservative local Python import closure for reviewed task runtimes.

This is not a general dependency resolver. Dynamic imports and data files must
be declared explicitly by the task gate. The trusted producer derives required
keys; a candidate manifest cannot choose which dependencies are checked.
"""
import ast
import importlib.util
from pathlib import Path


def local_import_closure(root, entries):
    root = Path(root).resolve()
    pending = list(entries)
    found = set()

    def module_files(name):
        parts = name.split('.')
        for end in range(1, len(parts) + 1):
            init = root.joinpath(*parts[:end], '__init__.py')
            if init.is_file():
                yield str(init.relative_to(root))
        source = root.joinpath(*parts).with_suffix('.py')
        if source.is_file():
            yield str(source.relative_to(root))

    while pending:
        name = pending.pop()
        if name in found:
            continue
        path = root / name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Missing or unsafe declared dependency: ' + name)
        found.add(name)
        if path.suffix != '.py':
            continue
        package = '.'.join(Path(name).parts[:-1])
        for node in ast.walk(ast.parse(path.read_text())):
            modules = []
            if isinstance(node, ast.Import):
                modules = [x.name for x in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = ('.' * node.level) + (node.module or '')
                if node.level:
                    base = importlib.util.resolve_name(base, package)
                modules = [base] + [base + '.' + x.name for x in node.names if x.name != '*']
            for module in modules:
                pending.extend(module_files(module))
    return sorted(found)
