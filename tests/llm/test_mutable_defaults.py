import ast
from pathlib import Path


def test_llm_ask_does_not_use_mutable_default_messages():
    repo_root = Path(__file__).resolve().parents[2]
    llm_dir = repo_root / "src" / "llm"

    paths = [llm_dir / "__init__.py"]
    paths.extend(sorted((llm_dir / "plugins").glob("*.py")))

    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "ask":
                assert not any(
                    isinstance(default, ast.List) for default in node.args.defaults
                ), f"{path} defines ask() with a mutable list default"
