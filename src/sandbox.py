"""Run Python code written by an LLM as safely as we reasonably can on a Windows laptop.

Three layers of protection:
1. A static check (reading the code without running it) rejects dangerous imports and calls,
   such as file deletion, subprocess, os.system, network libraries, or paths that point
   outside the working folder.
2. The code runs in a separate Python process, inside a fresh temporary folder, with read only
   copies of the data, a time limit, and a memory limit. The process is killed if it breaks a limit.
3. Inside that process a Python "audit hook" blocks the same dangerous actions at runtime, in case
   something slipped past the static check (for example a name built from strings).

This is a guard against accidents and simple misuse by a small model. It is not a security
boundary against a determined attacker; for that you would use a container or a virtual machine.
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import psutil

FORBIDDEN_MODULES = {
    "subprocess", "socket", "requests", "urllib", "urllib3", "http", "httpx", "aiohttp",
    "ftplib", "smtplib", "telnetlib", "paramiko", "shutil", "ctypes", "multiprocessing",
    "webbrowser", "pty", "winreg", "_winapi", "signal", "importlib", "builtins",
}
# Attribute calls that are forbidden no matter what object they are called on.
FORBIDDEN_ATTR_CALLS = {
    "system", "popen", "remove", "unlink", "rmdir", "removedirs", "rmtree", "rename",
    "replace", "kill", "startfile", "spawnl", "spawnv", "execv", "execl", "execve",
    "chmod", "chown", "truncate", "symlink", "link", "fork",
}
OS_ONLY = {"remove", "replace", "rename", "link", "truncate", "kill"}
FORBIDDEN_NAME_CALLS ={"eval", "exec", "compile", "__import__", "breakpoint", "input"}
ABS_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|[\\/]{1,2}\w|~)")


@dataclass
class StaticCheckResult:
    ok: bool
    problems: list[str] = field(default_factory=list)


def static_check(code: str) -> StaticCheckResult:
    """Return ok=False with a list of reasons if the code uses anything forbidden."""
    problems: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return StaticCheckResult(False, [f"SyntaxError: {e.msg} (line {e.lineno})"])

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                    problems.append(f"forbidden import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            if mod in FORBIDDEN_MODULES:
                problems.append(f"forbidden import: from {node.module}")
            if mod == "os":
                for alias in node.names:
                    if alias.name in FORBIDDEN_ATTR_CALLS:
                        problems.append(f"forbidden import: from os import {alias.name}")
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in FORBIDDEN_NAME_CALLS:
                problems.append(f"forbidden call: {f.id}()")
            if isinstance(f, ast.Attribute) and f.attr in FORBIDDEN_ATTR_CALLS:
                # list.remove, str.replace and DataFrame.rename are harmless and very common,
                # so these names are only forbidden when called on the os module itself.
                if f.attr in OS_ONLY and not (
                        isinstance(f.value, ast.Name) and f.value.id == "os"):
                    continue
                problems.append(f"forbidden call: .{f.attr}()")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value.strip()
            if "\n" not in s and len(s) < 300 and ABS_PATH.match(s):
                problems.append(f"path outside the working folder: {s!r}")
            if re.search(r"(^|[\\/])\.\.([\\/]|$)", s):
                problems.append(f"path leaving the working folder: {s!r}")
    # remove duplicates, keep order
    seen, unique = set(), []
    for p in problems:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return StaticCheckResult(not unique, unique)


# The runner script that executes inside the child process. It installs an audit hook that
# blocks dangerous actions, then runs solution.py as if it were the main program.
_RUNNER = r'''
import os, sys
_ROOT = os.path.realpath(os.getcwd())
_BLOCK_ALWAYS = {"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn",
                 "os.startfile", "os.kill", "socket.connect", "socket.bind", "socket.getaddrinfo",
                 "os.remove", "os.rmdir", "shutil.rmtree", "os.rename", "os.chmod", "os.truncate",
                 "winreg.OpenKey", "os.symlink", "os.link"}
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC

def _inside(path):
    try:
        p = os.path.realpath(os.fspath(path))
    except Exception:
        return False
    return p == _ROOT or p.startswith(_ROOT + os.sep)

def _hook(event, args):
    if event in _BLOCK_ALWAYS:
        if event in {"os.remove", "os.rename", "os.chmod", "os.truncate"} and args and _inside(args[0]) \
                and not os.path.realpath(os.fspath(args[0])).startswith(os.path.join(_ROOT, "data")):
            return  # removing or renaming your own scratch files inside the work folder is fine
        raise PermissionError(f"sandbox blocked: {event}")
    if event == "open" and len(args) >= 2:
        path, mode = args[0], args[1]
        writing = False
        if isinstance(mode, str):
            writing = any(c in mode for c in "wax+")
        elif isinstance(args[2] if len(args) > 2 else None, int):
            writing = bool(args[2] & _WRITE_FLAGS)
        if writing and isinstance(path, (str, bytes, os.PathLike)) and not _inside(path):
            raise PermissionError(f"sandbox blocked writing outside the work folder: {path}")

sys.addaudithook(_hook)
sys.argv = ["solution.py"]
import runpy
runpy.run_path("solution.py", run_name="__main__")
'''


@dataclass
class RunResult:
    status: str              # "ok", "error", "timeout", "memory", "rejected"
    returncode: int | None
    stdout: str
    stderr: str
    seconds: float
    rejected_reasons: list[str] = field(default_factory=list)
    peak_memory_mb: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def _make_writable_and_retry(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _copy_data_read_only(data_dir: Path, dest: Path) -> None:
    shutil.copytree(data_dir, dest)
    for p in dest.rglob("*"):
        if p.is_file():
            os.chmod(p, stat.S_IREAD)


def run_code(code: str, data_dir: str | Path | None = None, timeout_s: float = 120,
             max_memory_mb: float = 2048, max_output_chars: int = 4000,
             keep_dir: str | Path | None = None, _skip_static_check: bool = False) -> RunResult:
    """Static check, then run `code` in a fresh temporary folder with ./data as read only copies.

    `_skip_static_check` exists only so tests can prove the runtime layer works on its own.
    """
    check = static_check(code)
    if not check.ok and not _skip_static_check:
        return RunResult("rejected", None, "", "Rejected by the safety check:\n" +
                         "\n".join(f"- {p}" for p in check.problems), 0.0, check.problems)

    work = Path(tempfile.mkdtemp(prefix="sandbox_"))
    try:
        if data_dir is not None:
            _copy_data_read_only(Path(data_dir), work / "data")
        (work / "solution.py").write_text(code, encoding="utf-8")
        (work / "_runner.py").write_text(_RUNNER, encoding="utf-8")
        env = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),   # needed by Python on Windows
            "PATH": os.path.dirname(sys.executable),
            "TEMP": str(work), "TMP": str(work),
            "MPLCONFIGDIR": str(work / ".mpl"), "MPLBACKEND": "Agg",
            "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2", "MKL_NUM_THREADS": "2",
            "LOKY_MAX_CPU_COUNT": "1", "PYTHONIOENCODING": "utf-8",
        }
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        t0 = time.perf_counter()
        out_f = open(work / "_stdout.txt", "w+b")
        err_f = open(work / "_stderr.txt", "w+b")
        proc = subprocess.Popen([sys.executable, "-I", "-B", "_runner.py"], cwd=work, env=env,
                                stdout=out_f, stderr=err_f, stdin=subprocess.DEVNULL,
                                creationflags=flags)
        status, peak = None, 0.0
        ps = psutil.Process(proc.pid)
        while proc.poll() is None:
            elapsed = time.perf_counter() - t0
            try:
                mem = ps.memory_info().rss / 2**20
                peak = max(peak, mem)
            except psutil.Error:
                mem = 0.0
            if elapsed > timeout_s:
                status = "timeout"
            elif mem > max_memory_mb:
                status = "memory"
            if status:
                proc.kill()
                proc.wait()
                break
            time.sleep(0.1)
        seconds = time.perf_counter() - t0
        out_f.seek(0); err_f.seek(0)
        stdout = out_f.read().decode("utf-8", "replace")
        stderr = err_f.read().decode("utf-8", "replace")
        out_f.close(); err_f.close()
        if status == "timeout":
            stderr += f"\nKilled: the code ran longer than {timeout_s} seconds."
        elif status == "memory":
            stderr += f"\nKilled: the code used more than {max_memory_mb} MB of memory."
        else:
            status = "ok" if proc.returncode == 0 else "error"
        if keep_dir is not None:
            shutil.copy(work / "solution.py", Path(keep_dir) / "solution.py")
        return RunResult(status, proc.returncode, _tail(stdout, max_output_chars),
                         _tail(stderr, max_output_chars), round(seconds, 3),
                         peak_memory_mb=round(peak, 1))
    finally:
        shutil.rmtree(work, onerror=_make_writable_and_retry)


def _tail(s: str, n: int) -> str:
    return s if len(s) <= n else "...(earlier output cut)...\n" + s[-n:]
