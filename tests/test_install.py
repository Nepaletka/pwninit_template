import importlib.util
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", ROOT / "scripts/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def test_keep_templates_installs_new_commands_without_overwriting_custom_template(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config, zshrc = root / "config", root / ".zshrc"
            installer.install(config, zshrc, sys.executable, "pwninit")
            template = config / "pwninit-templates/default_template.py"
            template.write_text("my custom template")
            installer.install(config, zshrc, sys.executable, "pwninit", keep_templates=True)
            self.assertEqual(template.read_text(), "my custom template")
            self.assertTrue((config / "pwncompile.py").exists())
            command = "source " + shlex.quote(str(config / "pwninit.zsh")) + "\npwncompile --help"
            output = subprocess.check_output(["zsh", "-f", "-c", command], text=True)
            self.assertIn("Compile a C/C++ source", output)

    def test_templates_only_update_preserves_installed_tools(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "config"
            python, engine = "/existing/venv/bin/python", "/existing/tool/bin/pwninit"
            installer.install(config, root / ".zshrc", python, engine)
            subprocess.run([sys.executable, str(ROOT / "scripts/install.py"),
                            "--skip-deps", "--shell", "zsh", "--config-dir", str(config),
                            "--zshrc", str(root / ".zshrc")], check=True,
                           stdout=subprocess.DEVNULL)
            settings = json.loads((config / "pwninit.json").read_text())
            self.assertEqual(settings["python"], python)
            self.assertEqual(settings["engine"], engine)

    def test_zsh_migration_backup_and_idempotence(self):
        with tempfile.TemporaryDirectory(prefix="pwn install ") as folder:
            root = Path(folder)
            config, zshrc = root / "config with spaces", root / ".zshrc"
            original = "export EDITOR=vim\npwninit() {\n  echo old\n}\nalias ll='ls -l'\n"
            zshrc.write_text(original)
            installer.install(config, zshrc, sys.executable, "/unused/pwninit")
            first = zshrc.read_bytes()
            installer.install(config, zshrc, sys.executable, "/unused/pwninit")
            self.assertEqual(first, zshrc.read_bytes())
            self.assertEqual(zshrc.with_name(".zshrc.pwninit.bak").read_text(), original)
            self.assertIn("export EDITOR=vim", zshrc.read_text())
            self.assertIn("alias ll='ls -l'", zshrc.read_text())
            self.assertEqual(zshrc.read_text().count(installer.START), 1)
            self.assertNotIn("echo old", zshrc.read_text())
            result = subprocess.check_output([
                "zsh", "-f", "-c", "source " + shlex.quote(str(config / "pwninit.zsh")) +
                "\npwnpy -c 'print(123)'"], text=True)
            self.assertEqual(result.strip(), "123")

    def test_task_arguments_bindings_and_helpers(self):
        with tempfile.TemporaryDirectory(prefix="pwn task ") as folder:
            root = Path(folder)
            engine = root / "fake-pwninit"
            engine.write_text("#!" + sys.executable + "\n" + '''
import json, sys
from pathlib import Path
a = sys.argv[1:]
Path('arguments.json').write_text(json.dumps(a))
binary = Path(a[a.index('--bin')+1])
template = Path(a[a.index('--template-path')+1]).read_text()
bindings = 'exe = ELF(' + repr(str(binary)+'_patched') + ')\\nlibc = ELF("libc.so.6")\\nld = ELF("ld.so")'
Path('solve.py').write_text(template.format(bindings=bindings, bin_name='exe', proc_args='[exe.path]'))
''')
            engine.chmod(0o755)
            config = root / "config"
            installer.install(config, root / ".zshrc", sys.executable, str(engine))
            for heap in [False, True]:
                task = root / ("heap" if heap else "default")
                task.mkdir()
                (task / "target name").write_bytes(b"\x7fELFtest")
                command = [sys.executable, str(config / "pwninit-run.py")]
                if heap:
                    command.append("--heap")
                command += ["target name", "--no-patch-bin"]
                subprocess.run(command, cwd=task, check=True)
                args = json.loads((task / "arguments.json").read_text())
                self.assertEqual(args[args.index("--bin")+1], "target name")
                self.assertEqual(args[args.index("--template-bin-name")+1], "exe")
                self.assertIn("--no-patch-bin", args)
                solve = (task / "solve.py").read_text()
                compile(solve, "solve.py", "exec")
                self.assertIn("target name_patched", solve)
                self.assertNotIn("exe_patched", solve)
                self.assertTrue((task / "libs/debug.py").is_file())
                self.assertEqual((task / "libs/heap.py").exists(), heap)

    def test_macos_dependency_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(installer.platform, "system", return_value="Darwin"), \
                 patch.object(installer.shutil, "which", return_value="/opt/homebrew/bin/brew"), \
                 patch.object(installer.subprocess, "run") as run, \
                 patch.object(installer.subprocess, "check_output", side_effect=["/opt/homebrew\n", "/opt/homebrew/opt/python@3.13\n", "/opt/homebrew/opt/openssl@3\n"]):
                python, engine = installer.install_dependencies(Path(folder))
            calls = [call.args[0] for call in run.call_args_list]
            self.assertTrue(any("pwndbg/tap/pwndbg-gdb" in cmd for cmd in calls))
            self.assertIn("python@3.13", calls[0])
            self.assertIn("cmake", calls[0])
            self.assertTrue(any(cmd[0] == "/opt/homebrew/opt/python@3.13/bin/python3.13" and
                                "venv" in cmd for cmd in calls))
            self.assertTrue(any("pwntools>=4.14,<5" in cmd for cmd in calls))
            self.assertTrue(any("--locked" in cmd and "pwninit" in cmd for cmd in calls))
            self.assertTrue(python.endswith("pwninit-env-py313/bin/python"))
            self.assertTrue(engine.endswith("pwninit-tool/bin/pwninit"))

    def test_reject_macho_before_calling_upstream(self):
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder) / "mac-binary"
            binary.write_bytes(b"\xcf\xfa\xed\xfe")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/pwninit-run.py"),
                                     str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("expected a Linux ELF", result.stderr)

    @unittest.skipUnless(shutil.which("fish"), "fish is not installed")
    def test_fish_functions_paths_backup_and_cli(self):
        with tempfile.TemporaryDirectory(prefix="pwn fish ") as folder:
            root = Path(folder)
            config = root / "config's $literal"
            zshrc, fish_config = root / ".zshrc", config / "fish/conf.d/pwninit.fish"
            zshrc.write_text("do not change zsh\n")
            fish_config.parent.mkdir(parents=True)
            fish_config.write_text("# original fish integration\n")
            engine = root / "engine"
            engine.write_text("#!" + sys.executable + "\nimport sys\nprint(repr(sys.argv[1:]))\n")
            engine.chmod(0o755)
            binary = root / "target space"
            binary.write_bytes(b"\x7fELFtest")
            installer.install(config, zshrc, sys.executable, str(engine), "fish", fish_config)
            first = fish_config.read_bytes()
            installer.install(config, zshrc, sys.executable, str(engine), "fish", fish_config)
            self.assertEqual(first, fish_config.read_bytes())
            self.assertEqual(zshrc.read_text(), "do not change zsh\n")
            self.assertEqual(fish_config.with_name("pwninit.fish.pwninit.bak").read_text(),
                             "# original fish integration\n")
            command = ("source " + installer.fish_quote(fish_config) +
                       "\npwnpy -c 'print(123)'\npwncompile --help\npwninit --heap " + installer.fish_quote(binary))
            output = subprocess.check_output(["fish", "-N", "-c", command], text=True, cwd=root)
            self.assertIn("123", output)
            self.assertIn("--bin", output)
            self.assertIn("heap_template.py", output)
            self.assertIn("Compile a C/C++ source", output)
            self.assertTrue((root / "libs/debug.py").exists())
            result = subprocess.check_output([
                sys.executable, str(ROOT / "scripts/install.py"), "--skip-deps",
                "--shell", "fish", "--config-dir", str(config), "--zshrc", str(zshrc)
            ], text=True)
            self.assertIn("pwninit.fish", result)
            self.assertNotIn("source " + str(zshrc), result)

    def test_fish_parent_detected_even_if_login_shell_is_zsh(self):
        with patch.dict(installer.os.environ, {"SHELL": "/bin/zsh"}), \
             patch.object(installer.subprocess, "check_output", return_value="/opt/homebrew/bin/fish\n"):
            self.assertEqual(installer.detect_shell(), "fish")


if __name__ == "__main__":
    unittest.main()
