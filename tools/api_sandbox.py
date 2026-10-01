"""Restrict official subprocess commands to task files using Linux bubblewrap."""

from pathlib import Path
import sys


def install_isolation(bwrap: Path) -> None:
    import swegemma.sandbox.subprocess as backend

    original = backend.execute_subprocess_command

    def execute(*, command, cwd, env, timeout, shell=False):
        workspace = Path(cwd).resolve()
        root = workspace.parent
        if not (root / 'venv').is_dir():
            raise RuntimeError('Unexpected official sandbox layout')
        args = [str(bwrap), '--unshare-all', '--die-with-parent', '--new-session',
                '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin',
                '--symlink', 'usr/sbin', '/sbin', '--symlink', 'usr/lib', '/lib',
                '--symlink', 'usr/lib64', '/lib64', '--proc', '/proc', '--dev', '/dev',
                '--tmpfs', '/tmp']
        for location in ['/etc/alternatives', '/etc/hosts', '/etc/ssl/certs']:
            args += ['--ro-bind', location, location]
        # uv's venv symlinks can use the minor-version alias beside base_prefix.
        for location in {sys.prefix, str(Path(sys.base_prefix).parent)}:
            args += ['--ro-bind', location, location]
        task_deps = Path.home() / '.local/opt/gemma-task-deps'
        if not task_deps.is_dir():
            raise RuntimeError('Missing pinned task dependency overlay')
        args += ['--ro-bind', str(task_deps), str(task_deps)]
        args += ['--bind', str(root), str(root), '--chdir', str(workspace)]
        # Never inherit provider credentials, proxy variables or host search paths.
        clean = {k: v for k, v in env.items() if k in {
            'VIRTUAL_ENV', 'PYTHONPATH', 'TMPDIR', 'HOME', 'LANG', 'LC_ALL',
            'PYTHONNOUSERSITE', 'PYTHONUNBUFFERED', 'PIP_NO_INDEX',
        }}
        clean['PATH'] = f'{root}/venv/bin:{sys.prefix}/bin:/usr/bin:/bin'
        clean['HOME'] = str(root / 'tmp')
        clean['PYTHONPATH'] = f'{workspace}:{workspace}/src:{task_deps}'
        return original(command=args + command, cwd=workspace, env=clean,
                        timeout=timeout, shell=False)

    backend.execute_subprocess_command = execute


def check_isolation() -> None:
    from swegemma.sandbox import SubprocessManager
    manager = SubprocessManager()
    sid = manager.start()
    try:
        result = manager.exec(sid, "python -c 'import pathlib,socket; "
                              "assert not pathlib.Path(\"/mnt/c\").exists(); "
                              "assert not pathlib.Path(\"/proc/1/root/mnt/c\").exists(); "
                              "print(\"ISOLATED\")'")
        if result.exit_code or 'ISOLATED' not in result.stdout:
            raise RuntimeError(f'Isolation preflight failed: {result.stderr}')
    finally:
        manager.cleanup_all()
