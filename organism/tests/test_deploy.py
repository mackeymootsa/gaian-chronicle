"""Exercise the release controller against real, temporary Git repositories."""

import contextlib
import io
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deploy


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gaian-deploy-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repository = self.root / "upstream"
        self.repository.mkdir()
        self.runtime = self.root / "memory"
        self.runtime.mkdir()
        (self.runtime / "memory.json").write_text('"irreplaceable memory"')
        (self.runtime / ".env").write_text("export EXAMPLE_API_KEY=never-load-during-update\n")
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Offline deployment test")
        self.git("config", "user.email", "test@example.invalid")
        organism = self.repository / "organism"
        (organism / "config").mkdir(parents=True)
        (organism / "tests").mkdir()
        for file in ("pulse.py", "dream.py", "runtime.py", "entry.py"):
            (organism / file).write_text("# test fixture\n")
        (organism / "pulse.py").write_text(
            "import os\nfrom pathlib import Path\n"
            "Path(os.environ['NURSERY_DIR'], 'ran').write_text(os.environ['GAIAN_REVISION'])\n")
        (organism / "config" / "tela.json").write_text("{}\n")
        (organism / "tests" / "test_runtime.py").write_text(
            "import os, unittest\nclass ReleaseTest(unittest.TestCase):\n"
            "    def test_isolated_environment(self):\n"
            "        self.assertNotIn('EXAMPLE_API_KEY', os.environ)\n"
            f"        self.assertNotEqual(os.environ['NURSERY_DIR'], {str(self.runtime)!r})\n")
        self.first = self.commit("First release")
        self.deployment = deploy.Deployment(self.root / "deploy")
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)
        with patch.dict(os.environ, {"EXAMPLE_API_KEY": "must-not-be-inherited"}):
            self.deployment.install(self.runtime, str(self.repository))

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.repository), *args],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def test_install_preserves_runtime_and_activates_exact_revision(self):
        self.assertEqual(self.deployment.state()["current"], self.first)
        self.assertEqual((self.runtime / "memory.json").read_text(), '"irreplaceable memory"')
        self.assertEqual((self.runtime / ".env").read_text(), "export EXAMPLE_API_KEY=never-load-during-update\n")
        self.assertTrue((self.deployment.root / "manager.py").exists())
        self.assertEqual(self.deployment.run("pulse", ["tela"]), 0)
        self.assertEqual((self.runtime / "ran").read_text(), self.first)

    def test_unchanged_main_does_not_run_validation_again(self):
        with patch.object(self.deployment, "validate") as validate:
            self.deployment.update()
        validate.assert_not_called()

    def test_only_main_activates_and_next_job_uses_new_revision(self):
        self.git("switch", "-c", "proposal")
        self.commit("Unmerged idea")
        self.deployment.update()
        self.assertEqual(self.deployment.state()["current"], self.first)
        self.git("switch", "main")
        second = self.commit("Merged revision")
        self.deployment.update()
        self.assertEqual(self.deployment.state()["previous"], self.first)
        self.assertEqual(self.deployment.run("pulse", ["tela"]), 0)
        self.assertEqual((self.runtime / "ran").read_text(), second)

    def test_failed_validation_keeps_current_release_and_requires_retry(self):
        test = self.repository / "organism" / "tests" / "test_runtime.py"
        test.write_text("raise RuntimeError('broken candidate')\n")
        bad = self.commit("Broken tests")
        with self.assertRaisesRegex(RuntimeError, "broken candidate"):
            self.deployment.update()
        state = self.deployment.state()
        self.assertEqual(state["current"], self.first)
        self.assertEqual(state["failed_revision"], bad)
        with patch.object(self.deployment, "validate") as validate:
            self.deployment.update()
        validate.assert_not_called()
        with self.assertRaises(RuntimeError):
            self.deployment.update(retry=True)
        test.write_text("import unittest\nclass Fixed(unittest.TestCase):\n    def test_ok(self): pass\n")
        good = self.commit("Fix")
        self.deployment.update()
        self.assertEqual(self.deployment.state()["current"], good)

    def test_activation_defers_while_a_job_holds_shared_lock(self):
        second = self.commit("New main")
        with deploy.lock(self.deployment.root / "activation.lock", shared=True):
            self.deployment.update()
        self.assertEqual(self.deployment.state()["current"], self.first)
        self.assertIsNone(self.deployment.state()["failed_revision"])
        self.deployment.update()
        self.assertEqual(self.deployment.state()["current"], second)

    def test_pause_and_rollback_survive_polling_without_redeploying_bad_revision(self):
        second = self.commit("Second release")
        self.deployment.pause(True)
        self.deployment.update()
        self.assertEqual(self.deployment.state()["current"], self.first)
        self.assertEqual(self.deployment.run("pulse", ["tela"]), 0)
        self.deployment.pause(False)
        self.deployment.update()
        self.assertEqual(self.deployment.state()["current"], second)
        self.deployment.rollback()
        self.deployment.update()
        self.assertEqual(self.deployment.state()["current"], self.first)
        self.assertTrue(self.deployment.state()["paused"])

    def test_edited_candidate_is_preserved_and_rejected(self):
        second = self.commit("Second release")
        with deploy.lock(self.deployment.root / "activation.lock", shared=True):
            self.deployment.update()
        changed = self.deployment.releases / second / "organism" / "pulse.py"
        changed.write_text("# manual edit\n")
        with self.assertRaisesRegex(ValueError, "was edited"):
            self.deployment.update()
        self.assertEqual(changed.read_text(), "# manual edit\n")
        self.assertEqual(self.deployment.state()["current"], self.first)

    def test_remote_rewind_never_rolls_back_running_code(self):
        second = self.commit("Second release")
        self.deployment.update()
        self.git("reset", "--hard", self.first)  # Disposable upstream fixture only.
        with self.assertRaises(RuntimeError):
            self.deployment.update()
        self.assertEqual(self.deployment.state()["current"], second)

    def test_interrupted_activation_keeps_previous_pointer(self):
        self.commit("Second release")
        original = self.deployment.state_path.read_bytes()
        with patch.object(deploy.os, "replace", side_effect=OSError("simulated full disk")):
            with self.assertRaises(OSError):
                self.deployment.update()
        self.assertEqual(self.deployment.state_path.read_bytes(), original)

    def test_missing_release_and_invalid_job_cannot_touch_runtime(self):
        with self.assertRaisesRegex(ValueError, "mind"):
            self.deployment.run("pulse", ["../../secrets"])
        with self.assertRaisesRegex(ValueError, "No valid"):
            self.deployment.release("../upstream")
        self.assertFalse((self.runtime / "ran").exists())

    def test_cron_template_enables_only_selected_minds_and_never_sources_keys_for_update(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.deployment.cron(["tela"])
        active = [line for line in output.getvalue().splitlines() if not line.startswith("#")]
        self.assertEqual(len(active), 3)
        self.assertTrue(active[0].startswith("*/5 * * * *"))
        self.assertNotIn(".env", active[0])
        self.assertIn("prune", active[1])
        self.assertIn("run pulse tela", active[2])

    def test_prune_keeps_active_previous_and_runtime_files(self):
        for index in range(4):
            self.commit(f"Release {index}")
            self.deployment.update()
        before = (self.runtime / "memory.json").read_bytes()
        self.deployment.prune()
        self.assertEqual(len(list(self.deployment.releases.iterdir())), 3)
        state = self.deployment.state()
        self.assertTrue((self.deployment.releases / state["current"]).exists())
        self.assertTrue((self.deployment.releases / state["previous"]).exists())
        self.assertEqual((self.runtime / "memory.json").read_bytes(), before)

    def test_job_keeps_activation_lock_if_its_launcher_is_killed(self):
        script = self.repository / "organism" / "pulse.py"
        script.write_text("import os, sys\nprint('READY', flush=True)\nsys.stdin.read(1)\n")
        running = self.commit("Job that waits for local input")
        self.deployment.update()
        process = subprocess.Popen([sys.executable, "-B", str(self.deployment.root / "manager.py"),
                                    "run", "pulse", "tela"],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        try:
            ready, _, _ = select.select([process.stdout], [], [], 5)
            self.assertTrue(ready, "job did not become ready")
            self.assertEqual(process.stdout.readline(), b"READY\n")
            process.kill()  # Only the launcher; the scheduled job retains the fd.
            process.wait(timeout=5)
            self.commit("Candidate while orphaned job is active")
            self.deployment.update()
            self.assertEqual(self.deployment.state()["current"], running)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
            process.stdin.close()
            process.stdout.close()
            process.stderr.close()


if __name__ == "__main__":
    unittest.main()
