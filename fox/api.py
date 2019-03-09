import asyncio
import shlex
from .conf import env
from .connection import _get_connection
from .utils import CommandResult, read_from_stream, run_in_loop


def run(command, pty=False, cd=None) -> CommandResult:
    """Run a command on the current env.host_string remote host"""

    c = _get_connection(env.host_string)
    return c.run(command, pty, cd)


def sudo(command, pty=False, cd=None) -> CommandResult:
    """Run a command on the current env.host_string remote host with sudo"""

    c = _get_connection(env.host_string)
    return c.sudo(command, pty, cd)


def get(remotefile, localfile):
    """Download a file from the remote server."""

    c = _get_connection(env.host_string)
    c.get(remotefile, localfile)


def put(localfile, remotefile):
    """Upload a local file to a remote server."""

    c = _get_connection(env.host_string)
    c.put(localfile, remotefile)


def read(remotefile) -> bytes:
    """Read the contents of a remote file."""

    c = _get_connection(env.host_string)
    return c.read(remotefile)


def file_exists(remotefile) -> bool:
    """Check if a file exists on the remote server."""

    c = _get_connection(env.host_string)
    return c.file_exists(remotefile)


async def _local(command, **kwargs) -> CommandResult:
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
    proc = await asyncio.create_subprocess_exec(*cmdline, **args)  # type: ignore
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


def local(command, cd=None) -> CommandResult:
    """Execute `command` on the local machine."""

    kwargs = {"cd": cd}
    return run_in_loop(_local(command, **kwargs))


def run_concurrent(hosts, command, limit=0):
    """Execute `command` on `hosts` concurrently."""

    return run_in_loop(_run_concurrent(hosts, command, limit))


async def _run_concurrent(hosts, command, pty=False, cd=None, limit=0):
    conns = [_get_connection(host) for host in hosts]
    futures_done = []

    aws = set()
    while conns:
        conn = conns.pop(0)
        aws.add(asyncio.ensure_future(conn._run(command, pty=pty, cd=cd)))
        if limit and len(aws) >= limit:
            done, pending = await asyncio.wait(aws, return_when=asyncio.FIRST_COMPLETED)
            aws = pending
            futures_done.extend(done)

    if len(aws):
        done, pending = await asyncio.wait(aws, return_when=asyncio.ALL_COMPLETED)
        futures_done.extend(done)

    return [future.result() for future in futures_done]
