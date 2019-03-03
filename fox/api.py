import asyncio
import shlex
from .conf import env
from .connection import _get_connection
from .utils import CommandResult, read_from_stream, run_in_loop


def run(command, pty=False, cd=None):
    """Run a command on the current env.host_string remote host"""

    c = _get_connection(env.host_string)
    c.run(command, pty, cd)


def sudo(command, pty=False, cd=None):
    """Run a command on the current env.host_string remote host with sudo"""

    c = _get_connection(env.host_string)
    c.sudo(command, pty, cd)


def get(remotefile, localfile):
    c = _get_connection(env.host_string)
    c.get(remotefile, localfile)


def put(localfile, remotefile):
    c = _get_connection(env.host_string)
    c.put(localfile, remotefile)


def read(remotefile) -> bytes:
    c = _get_connection(env.host_string)
    return c.read(remotefile)


def file_exists(remotefile) -> bool:
    c = _get_connection(env.host_string)
    return c.file_exists(remotefile)


async def _local(command, **kwargs):
    args = {
        "cwd": kwargs.get("cd"),
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.PIPE,
    }
    label = "*local*"
    original_command = command
    cmdline = shlex.split(command)

    # NOTES:
    # - this must not be called with shell=True; see:
    # https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.subprocess_exec
    proc = await asyncio.create_subprocess_exec(*cmdline, **args)
    stdout, stderr = await asyncio.gather(
        read_from_stream(proc.stdout, proc.stdin, label, decode=True),
        read_from_stream(proc.stderr, proc.stdin, label, decode=True),
    )

    await proc.wait()
    return CommandResult(
        command=original_command,
        actual_command=command,
        exit_code=proc.returncode,
        stdout=stdout,
        # if we use a pty this will be empty
        stderr=stderr,
        hostname="*local*",
    )


def local(command, cd=None):
    kwargs = {"cd": cd}
    return run_in_loop(_local(command, **kwargs))
