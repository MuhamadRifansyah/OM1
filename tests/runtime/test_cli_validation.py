import os
import tempfile
from cli import _check_class_in_dir


def test_check_class_in_dir_handles_syntax_error(capsys):
    """
    Verify that _check_class_in_dir catches SyntaxError in plugin files
    and logs a warning instead of silently failing or crashing.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Create a dummy python file with a syntax error (missing colon)
        bad_file = os.path.join(tmp_dir, "bad_plugin.py")
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("class BrokenPlugin\n    pass")

        # 2. Create a valid plugin file
        good_file = os.path.join(tmp_dir, "good_plugin.py")
        with open(good_file, "w", encoding="utf-8") as f:
            f.write("class ValidPlugin:\n    pass")

        # 3. Check for the valid plugin. The parser should encounter the bad file,
        #    log a warning, and continue to find the valid plugin.
        exists = _check_class_in_dir(tmp_dir, "ValidPlugin")

        assert exists is True, "Should find ValidPlugin despite syntax error in sibling file"

        # 4. Verify the warning was printed to stdout
        captured = capsys.readouterr()
        assert "Warning: Syntax error parsing" in captured.out
        assert "bad_plugin.py" in captured.out