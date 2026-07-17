import subprocess
import sys
from pathlib import Path
import tomllib
import os
import builtins
import stat
import shlex
import tomlkit
from types import FunctionType,ModuleType
'''
Expect the following fs:
.
├── validator.py
├── runner.py
├── pyproject.toml
├── pipe
└── flower/
    ├── client.py
    ├── server.py
    ├── pyproject.toml ( created by runner )
    └── user/
        ├── exports.py
        └── ...etc
'''

USER_PROJECT = Path("flower/user")
RUN_DIR = Path("flower")
IN_PIPE = Path(".pipes/in.pipe")
OUT_PIPE = Path(".pipes/out.pipe")
TEMPLATE_PYPROJECT = Path(
    "pyproject.toml"
)

class DummyModule(ModuleType):
    def __getattr__(self, key):
        return None
    __all__ = []   # support wildcard imports

MOCK_CACHE = {}

realimport = builtins.__import__

def tryimport(name, globals={}, locals={}, fromlist=[], level=0):
    try:
        return realimport(name, globals, locals, fromlist, level)
    except ImportError:
        root_name = name.split('.')[0]
        if root_name not in MOCK_CACHE:
            print(f"Mocking missing dependency: '{root_name}'",flush=True)
            MOCK_CACHE[root_name] = DummyModule(root_name)
        return MOCK_CACHE[root_name]

builtins.__import__ = tryimport

def load_exports():
    for key in list(sys.modules.keys()):
        if key == "flower.user.exports" or key.startswith("flower.user.exports."):
            del sys.modules[key]
    import flower.user.exports as exports
    return exports

def validate_exports(exports):
    class ExportsValidationError(BaseException):
        pass

    errors = []

    # train
    if not hasattr(exports, "train"):
        errors.append("Missing required object: train")
    elif not isinstance(exports.train, FunctionType):
        errors.append(
            f"train must be a function, got {type(exports.train).__name__}"
        )

    # evaluate
    if not hasattr(exports, "evaluate"):
        errors.append("Missing required object: evaluate")
    elif not isinstance(exports.evaluate, FunctionType):
        errors.append(
            f"evaluate must be a function, got {type(exports.evaluate).__name__}"
        )

    # DEPENDENCIES
    if not hasattr(exports, "DEPENDENCIES"):
        errors.append("Missing required object: DEPENDENCIES")
    else:
        deps = exports.DEPENDENCIES

        if not isinstance(deps, list):
            errors.append(
                f"DEPENDENCIES must be a list, got {type(deps).__name__}"
            )
        else:
            for i, dep in enumerate(deps):
                if not isinstance(dep, str):
                    errors.append(
                        f"DEPENDENCIES[{i}] must be a string, got {type(dep).__name__}"
                    )

    # CAPABILITIES
    if not hasattr(exports, "CAPABILITIES"):
        errors.append("Missing required object: CAPABILITIES")
    else:
        caps = exports.CAPABILITIES

        if not isinstance(caps, dict):
            errors.append(
                f"CAPABILITIES must be a dict, got {caps}"
            )
        else:
            for k,v in caps.items():

                if not isinstance(v, str) or not isinstance(k,str) :
                    errors.append(
                        f"CAPABILITIES[{k}:{v}] must be a string, got {type(k).__name__}:{type(v).__name__}"
                    )
                    continue

    if errors:
        raise ExportsValidationError(
            "exports.py validation failed:\n\n"
            + "\n".join(f"- {e}" for e in errors)
        )

    print("exports.py validation successful",flush=True)

def generate_pyproject(exports=None):
    """
    Loads template pyproject.toml and injects:

    - user dependencies
    - capability declarations
    """
    with open(
        TEMPLATE_PYPROJECT,
        "rb"
    ) as f:
        project = tomllib.load(f)

    if exports != None:
        dependencies = (
            project
            .setdefault("project", {})
            .setdefault("dependencies", [])
        )
        for dependency in exports.DEPENDENCIES:
            if dependency not in dependencies:
                print(f"found dependency: {dependency}",flush=True)
                dependencies.append(
                    dependency
                )
        capabilities = (
            project
            .setdefault("tool", {})
            .setdefault("flwr", {})
            .setdefault("app", {})
            .setdefault("config", {})
            .setdefault("capabilities", {})
        )
        for k,v in exports.CAPABILITIES.items():
            print(f"adding capability: {k}:{v}",flush=True)
            capabilities[k] = v

    with open(
        RUN_DIR / "pyproject.toml",
        "w"
    ) as f:
        f.write(tomlkit.dumps(project))
        
def setup_pipes():
    IN_PIPE.parent.mkdir(parents=True, exist_ok=True)
    for pipe_path in (IN_PIPE, OUT_PIPE):
        if not pipe_path.exists():
            os.mkfifo(pipe_path)
            os.chmod(pipe_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)

def listen():
    print(f"Listening to {IN_PIPE}... Press [CTRL+C] to exit.", flush=True)
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    while True:
        with open(IN_PIPE, "r") as in_f:
            
            for line in in_f:
                line = line.strip()
                if not line:
                    continue
                
                cmd_args = shlex.split(line)
                with open(OUT_PIPE, "w") as out_f:
                    try:
                        sys.stdout = out_f
                        sys.stderr = out_f
                        execute(cmd_args)
                        
                    except Exception as e:
                        out_f.write(f"[Orchestrator Failure]: Exception caught runtime: {e}\n")
                    finally:
                        sys.stdout = original_stdout
                        sys.stderr = original_stderr
def execute(args):
    if not args:
        print("Error: No verb passed to runner execution layer.", file=sys.stderr, flush=True)
        return 1
    verb = args[0]
    if verb == "run":
        exports = load_exports()
        validate_exports(exports)
        generated_toml = RUN_DIR / "pyproject.toml"
        if generated_toml.exists():
            try:
                os.remove(generated_toml)
                print(f"Cleaned up legacy configuration: {generated_toml}",flush=True)
            except OSError as e:
                print(f"Warning: Could not remove old config ({e.strerror}). Attempting overwrite...", file=sys.stderr,flush=True)
        generate_pyproject(exports)
    else:
        generate_pyproject(None)
    proc = subprocess.Popen(
        ["flwr",*args],
        cwd=RUN_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    for line in proc.stdout:
        print(line, end="", flush=True)
        
    return proc.wait()

if __name__ == "__main__":
    try:
        setup_pipes()
        listen()
    except KeyboardInterrupt:
        sys.exit(0)