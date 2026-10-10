import atexit
import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(rel, name):
    """Import an extension-less script (bin/octl, bin/consult, hooks/scripts/*.py) as a module."""
    path = os.path.join(KIT, rel)
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_DIRS = []
atexit.register(lambda: [shutil.rmtree(d, ignore_errors=True) for d in _DIRS])


def tmpdir(prefix="kit-test-"):
    d = tempfile.mkdtemp(prefix=prefix)
    _DIRS.append(d)
    return d


def project(cfg=None):
    """Temp project dir with an octl.json; returns (dir, config path)."""
    d = tmpdir()
    path = os.path.join(d, "octl.json")
    with open(path, "w") as fh:
        json.dump(cfg if cfg is not None else {"repo": "acme/app", "base_branch": "develop"}, fh)
    return d, path
