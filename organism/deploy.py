#!/usr/bin/env python3
"""Small, host-installed release controller. No model calls or runtime migrations.

The installed copy deliberately stays independent of the deployed application so
it can still pause and roll back a broken release. See DEPLOYMENT.md.
"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

REPOSITORY = "https://github.com/mackeymootsa/gaian-chronicle.git"
DEFAULT_DEPLOY = Path("/var/opt/quadrumvirate/deploy")
DEFAULT_RUNTIME = Path("/var/opt/quadrumvirate/nursery")
SHA = re.compile(r"[0-9a-f]{40}")
MIND = re.compile(r"[a-z][a-z0-9_-]{0,31}")
CONTROLLER_VERSION = 1
JOB_SCRIPTS = {"pulse": "pulse.py", "dream": "dream.py",
               "archive": "archive-logs.sh", "buffer": "check-buffer.sh"}


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_atomic(path, value):
    """Standalone: recovery must not import code from a potentially bad release."""
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


@contextmanager
def lock(path, *, shared=False):
    with path.open("a") as stream:
        fcntl.flock(stream, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        # A child inherits this descriptor: killing its launcher does not release
        # the activation lock while the actual job is still running.
        yield stream.fileno()


def clean_env(temporary):
    """Validation/fetch never inherit API keys, runtime paths, or Git overrides."""
    return {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(temporary),
            "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
            "NURSERY_DIR": str(Path(temporary) / "nursery"),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0"}


def command(args, *, env, cwd=None, timeout=120):
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True,
                            timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} failed ({result.returncode}): "
                           f"{(result.stdout + result.stderr)[-6000:]}")
    return result.stdout.strip()


class Deployment:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.config_path = self.root / "config.json"
        self.state_path = self.root / "state.json"
        self.cache = self.root / "repository.git"
        self.releases = self.root / "releases"

    def config(self):
        return json.loads(self.config_path.read_text())

    def state(self):
        state = json.loads(self.state_path.read_text())
        if not isinstance(state, dict) or not isinstance(state.get("paused"), bool):
            raise ValueError("Invalid deployment state; restore from backup before continuing")
        for key in ("current", "previous"):
            if state.get(key) is not None and not SHA.fullmatch(str(state[key])):
                raise ValueError(f"Invalid {key} revision")
        return state

    def save(self, state, message):
        state["updated_at"] = now()
        state["message"] = message
        write_atomic(self.state_path, json.dumps(state, indent=2) + "\n")
        print(message)

    def install(self, runtime, repository=REPOSITORY):
        runtime = Path(runtime).resolve()
        if runtime == self.root or self.root in runtime.parents or runtime in self.root.parents:
            raise ValueError("Runtime and deployment directories must be separate, non-nested paths")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with lock(self.root / "update.lock"):
            if self.config_path.exists() or self.state_path.exists():
                raise ValueError("Already installed; use update, or the documented controller upgrade")
            self.releases.mkdir(mode=0o700, exist_ok=True)
            # Do not create, read, move, or replace runtime state or secrets.
            write_atomic(self.root / "manager.py", Path(__file__).read_text())
            write_atomic(self.config_path, json.dumps({"repository": repository,
                "branch": "main", "runtime_dir": str(runtime),
                "controller_version": CONTROLLER_VERSION}, indent=2) + "\n")
            self.save({"current": None, "previous": None, "paused": False,
                       "failed_revision": None}, "Installed controller; awaiting first release")
        return self.update()

    def git(self, *args, env):
        return command(["git", "--git-dir", str(self.cache), *args], env=env)

    def release(self, revision):
        if not revision or not SHA.fullmatch(revision):
            raise ValueError("No valid active release")
        path = self.releases / revision
        if path.is_symlink() or not path.is_dir():
            raise ValueError(f"Missing or redirected release: {revision}")
        return path

    def check_tree(self, release, revision, env):
        head = command(["git", "-C", str(release), "rev-parse", "HEAD"], env=env)
        dirty = command(["git", "-C", str(release), "status", "--porcelain",
                         "--untracked-files=all"], env=env)
        if head != revision or dirty:
            raise ValueError("Managed release was edited; preserve it for review, do not reset it")

    def validate(self, release, env):
        required = [f"organism/{script}" for script in JOB_SCRIPTS.values()]
        required += ["organism/entry.py", "organism/runtime.py", "organism/tests/test_runtime.py"]
        for name in required:
            path = release / name
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"Missing regular release file: {name}")
        for path in (release / "organism").rglob("*.py"):
            compile(path.read_bytes(), str(path), "exec")
        for path in (release / "organism" / "config").glob("*.json"):
            json.loads(path.read_text())
        for path in (release / "organism").rglob("*.sh"):
            command(["bash", "-n", str(path)], env=env, timeout=10)
        command([sys.executable, "-B", "-m", "unittest", "discover",
                 "-s", "organism/tests", "-v"], cwd=release, env=env, timeout=180)

    def update(self, retry=False):
        with lock(self.root / "update.lock"):
            state = self.state()
            if state["paused"]:
                print("PAUSED: updates are disabled; scheduled jobs still use the current release")
                return
            candidate = None
            try:
                with tempfile.TemporaryDirectory(prefix="gaian-validation-") as temporary:
                    env = clean_env(temporary)
                    if not self.cache.exists():
                        command(["git", "init", "--bare", str(self.cache)], env=env)
                    config = self.config()
                    # The branch is fixed. PR branches and tags cannot activate code.
                    self.git("fetch", "--no-tags", config["repository"],
                             "refs/heads/main:refs/remotes/origin/main", env=env)
                    candidate = self.git("rev-parse", "refs/remotes/origin/main^{commit}", env=env)
                    if candidate == state["current"]:
                        self.check_tree(self.release(candidate), candidate, env)
                        print(f"CURRENT: {candidate}")
                        return
                    if candidate == state.get("failed_revision") and not retry:
                        print(f"REJECTED: {candidate}; use update --retry after reviewing the failure")
                        return
                    if state["current"]:
                        self.git("merge-base", "--is-ancestor", state["current"], candidate, env=env)
                    path = self.releases / candidate
                    if not path.exists():
                        self.git("worktree", "add", "--detach", str(path), candidate, env=env)
                    release = self.release(candidate)
                    self.check_tree(release, candidate, env)
                    self.validate(release, env)
                    self.check_tree(release, candidate, env)
                # Preparation does not interrupt pulses. Switch only when all
                # launched jobs are idle; otherwise retry on the next cron tick.
                with lock(self.root / "activation.lock"):
                    state["previous"] = state["current"]
                    state["current"] = candidate
                    state["failed_revision"] = None
                    self.save(state, f"ACTIVATED: {candidate}; previous={state['previous']}")
            except BlockingIOError:
                print("DEFERRED: a runtime job is active; retry on the next update")
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                state["failed_revision"] = candidate
                self.save(state, f"UPDATE_FAILED: {str(error)[-6500:]}")
                raise

    def pause(self, paused):
        with lock(self.root / "update.lock"):
            state = self.state()
            state["paused"] = paused
            self.save(state, "PAUSED: updates disabled" if paused else "RESUMED: next update may activate main")

    def rollback(self):
        with lock(self.root / "update.lock"), lock(self.root / "activation.lock"):
            state = self.state()
            target = self.release(state["previous"])
            with tempfile.TemporaryDirectory(prefix="gaian-rollback-") as temporary:
                self.check_tree(target, state["previous"], clean_env(temporary))
            state["current"], state["previous"] = state["previous"], state["current"]
            state["paused"] = True
            self.save(state, f"ROLLED_BACK: {state['current']}; updates paused until resume")

    def prune(self):
        """Remove only old, clean managed code copies; never runtime history."""
        with lock(self.root / "update.lock"), lock(self.root / "activation.lock"):
            state = self.state()
            releases = sorted((p for p in self.releases.iterdir()
                               if SHA.fullmatch(p.name) and p.is_dir() and not p.is_symlink()),
                              key=lambda p: p.stat().st_mtime, reverse=True)
            keep = {state["current"], state["previous"], state.get("failed_revision")}
            keep.update(p.name for p in releases[:3])
            with tempfile.TemporaryDirectory(prefix="gaian-prune-") as temporary:
                env = clean_env(temporary)
                for path in releases:
                    if path.name in keep:
                        continue
                    self.check_tree(path, path.name, env)
                    # No --force: Git also refuses unknown worktrees and edits.
                    self.git("worktree", "remove", str(path), env=env)
                    print(f"PRUNED code release: {path.name}")

    def run(self, job, arguments):
        if job not in JOB_SCRIPTS:
            raise ValueError("Unknown job")
        if job == "pulse" and (len(arguments) != 1 or not MIND.fullmatch(arguments[0])):
            raise ValueError("pulse requires one mind name")
        if job == "dream" and (len(arguments) != 2 or not MIND.fullmatch(arguments[0])
                               or arguments[1] not in ("daily", "weekly")):
            raise ValueError("dream requires a mind and daily or weekly")
        if job in ("archive", "buffer") and arguments:
            raise ValueError(f"{job} takes no arguments")
        with lock(self.root / "activation.lock", shared=True) as descriptor:
            state = self.state()
            release = self.release(state["current"])
            # Check locally even when updates are paused or GitHub is unreachable.
            # Keep the activation lock through this check and the child process.
            with tempfile.TemporaryDirectory(prefix="gaian-run-check-") as temporary:
                self.check_tree(release, state["current"], clean_env(temporary))
            script = release / "organism" / JOB_SCRIPTS[job]
            config = self.config()
            env = {**os.environ, "NURSERY_DIR": config["runtime_dir"],
                   "GAIAN_DEPLOY_DIR": str(self.root), "GAIAN_REVISION": state["current"],
                   "PYTHONDONTWRITEBYTECODE": "1"}
            executable = ["bash"] if script.suffix == ".sh" else [sys.executable, "-B"]
            return subprocess.call(executable + [str(script), *arguments], cwd=release,
                                   env=env, pass_fds=(descriptor,))

    def cron(self, minds):
        """A reviewable template, never an implicit crontab replacement."""
        if not minds or len(set(minds)) != len(minds) or any(m not in ("tela", "nowa", "tecton") for m in minds):
            raise ValueError("Choose distinct minds from tela, nowa, tecton")
        if any(c in str(self.root) + self.config()["runtime_dir"] for c in ("\n", "\r", "%")):
            raise ValueError("Cron paths cannot contain newlines or percent signs")
        manager = shlex.quote(str(self.root / "manager.py"))
        env_file = shlex.quote(str(Path(self.config()["runtime_dir"]) / ".env"))
        log = shlex.quote(str(self.root / "update.log"))
        print("# Replace old organism jobs; preserve unrelated crontab entries.")
        print("# The updater never loads API keys. update.log holds the latest attempt.")
        print(f"*/5 * * * * /usr/bin/python3 {manager} update > {log} 2>&1")
        print(f"17 3 * * 0 /usr/bin/python3 {manager} prune")
        for mind in minds:
            offset = {"tela": 0, "nowa": 20, "tecton": 40}[mind]
            print(f"{offset} * * * * . {env_file} && /usr/bin/python3 {manager} run pulse {mind}")
        print("# Preserve any existing dream cadence, replacing its command with:")
        print(f"# . {env_file} && /usr/bin/python3 {manager} run dream tela daily")
        print(f"# . {env_file} && /usr/bin/python3 {manager} run dream tela weekly")
        print(f"# Optional existing archive job: /usr/bin/python3 {manager} run archive")


def main():
    installed = Path(__file__).name == "manager.py"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deploy-dir", type=Path,
                        default=Path(__file__).resolve().parent if installed else DEFAULT_DEPLOY)
    sub = parser.add_subparsers(dest="action", required=True)
    install = sub.add_parser("install")
    install.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    update = sub.add_parser("update")
    update.add_argument("--retry", action="store_true")
    for name in ("pause", "resume", "rollback", "status", "prune"):
        sub.add_parser(name)
    run = sub.add_parser("run")
    run.add_argument("job", choices=JOB_SCRIPTS)
    run.add_argument("arguments", nargs="*")
    cron = sub.add_parser("cron")
    cron.add_argument("--mind", action="append", dest="minds")
    args = parser.parse_args()
    os.umask(0o077)
    deployment = Deployment(args.deploy_dir)
    try:
        if args.action == "install":
            deployment.install(args.runtime_dir)
        elif args.action == "update":
            deployment.update(args.retry)
        elif args.action in ("pause", "resume"):
            deployment.pause(args.action == "pause")
        elif args.action == "rollback":
            deployment.rollback()
        elif args.action == "prune":
            deployment.prune()
        elif args.action == "status":
            print(json.dumps(deployment.state(), indent=2))
        elif args.action == "run":
            return deployment.run(args.job, args.arguments)
        elif args.action == "cron":
            deployment.cron(args.minds or ["tela"])
    except BlockingIOError:
        print("BUSY: another update, activation, or job holds the lock; retry later")
        return 0 if args.action in ("update", "run") else 1
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
