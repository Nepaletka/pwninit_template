import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("compiler", ROOT / "scripts/pwncompile.py")
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)


class CompileTests(unittest.TestCase):
    def test_failed_compilation_preserves_output_and_cleans_remote(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / "test.c", Path(folder) / "chall"
            source.write_text("invalid C")
            output.write_bytes(b"previous executable")
            calls = []

            def run(command, **kwargs):
                calls.append(command)
                if command[-1].startswith("cd "):
                    raise subprocess.CalledProcessError(1, command)
                return subprocess.CompletedProcess(command, 0)

            with patch.object(compiler.subprocess, "check_output", return_value="/tmp/pwncompile.ABC123\n"), \
                 patch.object(compiler.subprocess, "run", side_effect=run):
                with self.assertRaises(subprocess.CalledProcessError):
                    compiler.compile_source(source, output)
            self.assertEqual(output.read_bytes(), b"previous executable")
            self.assertTrue(calls[-1][-1].startswith("rm -rf -- /tmp/pwncompile."))
            self.assertFalse(any(command[0] == "scp" for command in calls))

    def test_non_elf_download_does_not_replace_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / "test.c", Path(folder) / "chall"
            source.write_text("int main(void) { return 0; }")
            output.write_bytes(b"previous executable")
            calls = []

            def run(command, **kwargs):
                calls.append(command)
                if command[0] == "scp":
                    Path(command[-1]).write_bytes(b"not an ELF")
                return subprocess.CompletedProcess(command, 0)

            with patch.object(compiler.subprocess, "check_output", return_value="/tmp/pwncompile.ABC123\n"), \
                 patch.object(compiler.subprocess, "run", side_effect=run):
                with self.assertRaisesRegex(RuntimeError, "not a Linux ELF"):
                    compiler.compile_source(source, output)
            self.assertEqual(output.read_bytes(), b"previous executable")
            self.assertTrue(calls[-1][-1].startswith("rm -rf"))
            self.assertFalse(list(Path(folder).glob(".pwncompile-*")))


if __name__ == "__main__":
    unittest.main()
