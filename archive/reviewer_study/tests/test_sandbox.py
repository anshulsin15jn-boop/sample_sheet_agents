"""Tests for the sandbox: safe code runs, dangerous code is blocked."""
import os
from pathlib import Path

import pytest

from src.sandbox import run_code, static_check


DANGEROUS = [
    "import os\nos.system('echo hacked')",
    "import subprocess\nsubprocess.run(['dir'])",
    "import shutil\nshutil.rmtree('data')",
    "import os\nos.remove('data/x.csv')",
    "import requests\nrequests.get('http://example.com')",
    "from urllib.request import urlopen\nurlopen('http://example.com')",
    "import socket\nsocket.socket()",
    "from pathlib import Path\nPath('data/x.csv').unlink()",
    "open('C:/Users/someone/evil.txt', 'w').write('x')",
    "open('../escape.txt', 'w').write('x')",
    "eval('1+1')",
    "__import__('os').system('echo hi')",
]


@pytest.mark.parametrize("code", DANGEROUS)
def test_static_check_blocks_dangerous_code(code):
    assert not static_check(code).ok


def test_static_check_allows_normal_analysis_code():
    code = (
        "import pandas as pd\nimport numpy as np\n"
        "df = pd.read_csv('data/x.csv')\n"
        "df = df.replace(-999, np.nan).rename(columns={'a': 'b'})\n"
        "cols = list(df.columns); cols.remove('b')\n"
        "print('ANSWER:', {'n': len(df)})\n"
    )
    assert static_check(code).ok, static_check(code).problems


def test_dangerous_snippet_is_rejected_and_not_run(tmp_path):
    marker = tmp_path / "should_not_exist.txt"
    code = f"import os\nos.system('echo x > \"{marker}\"')\n"
    res = run_code(code)
    assert res.status == "rejected"
    assert not marker.exists()
    assert any("os" in r or "path" in r for r in res.rejected_reasons)


def test_runtime_hook_blocks_dynamic_escape():
    # Builds the module name from strings so the static check cannot see it.
    code = "m = getattr(__builtins__, '__imp' + 'ort__') if not isinstance(__builtins__, dict) " \
           "else __builtins__['__imp' + 'ort__']\nm('o' + 's').system('echo hi')\n"
    assert not static_check(code).ok          # layer 1 catches it
    res = run_code(code, _skip_static_check=True)   # layer 2 catches it too
    assert res.status == "error"
    assert "sandbox blocked" in res.stderr


def test_runtime_hook_blocks_writing_outside(tmp_path):
    target = str(tmp_path / "outside.txt").replace("\\", "/")
    # Hide the absolute path from the static check by splitting it.
    a, b = target[:3], target[3:]
    code = f"p = {a!r} + {b!r}\nopen(p, 'w').write('x')\n"
    res = run_code(code, _skip_static_check=True)
    assert res.status == "error"
    assert not Path(target).exists()


def test_normal_code_runs_and_reads_read_only_data(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "x.csv").write_text("a,b\n1,2\n3,4\n")
    code = ("import pandas as pd, json\n"
            "df = pd.read_csv('data/x.csv')\n"
            "df.to_csv('my_output.csv')\n"   # writing inside the work folder is allowed
            "print('ANSWER: ' + json.dumps({'total': int(df.a.sum())}))\n")
    res = run_code(code, data_dir=data)
    assert res.ok, res.stderr
    assert 'ANSWER: {"total": 4}' in res.stdout


def test_data_copy_is_read_only(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "x.csv").write_text("a\n1\n")
    res = run_code("open('data/x.csv', 'a').write('2\\n')\n", data_dir=data)
    assert res.status == "error"
    assert (data / "x.csv").read_text() == "a\n1\n"   # original untouched


def test_timeout_kills_process():
    res = run_code("import time\nwhile True:\n    time.sleep(0.05)\n", timeout_s=2)
    assert res.status == "timeout"
    assert res.seconds < 10


def test_syntax_error_is_reported():
    res = run_code("def f(:\n  pass\n")
    assert res.status == "rejected"
    assert "SyntaxError" in res.stderr
