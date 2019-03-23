import os
import asyncio
import shlex
from .conf import env
from .connection import _get_connection
from .utils import CommandResult, read_from_stream, run_in_loop


def run(command, pty=False, cd=None, environ=None, echo=True) -> CommandResult:
    """Run a command on the current `env.host_string` remote host.

    :param command: the command line string to execute.
    :param pty: wether to request a remote pty.
    :param cd: the optional name of the directory where the command will be executed.
    :param environ: an optional dictionary containing environment variables to set when
    executing the command.
    :param echo: set to `False` to hide the output of the command.
    """

    c = _get_connection(env.host_string)
    return c.run(command, pty, cd)


def sudo(command, pty=False, cd=None, environ=None, echo=True) -> CommandResult:
    """Run a command on the current env.host_string remote host with sudo

    :param command: the command line string to execute.
    :param pty: wether to request a remote pty.
    :param cd: the optional name of the directory where the command will be executed.
    :param environ: an optional dictionary containing environment variables to set when
    executing the command.
    :param echo: set to `False` to hide the output of the command.
    """

    c = _get_connection(env.host_string)
    return c.sudo(command, pty, cd)


def get(remotefile, localfile):
    """Download a file from the remote server.

    :param remotefile: the path to the remote file to download.
    :param localfile: the local path where to write the downloaded file.
    """

    c = _get_connection(env.host_string)
    c.get(remotefile, localfile)


def put(localfile, remotefile):
    """Upload a local file to a remote server.

    :param localfile: the path of the local file to upload.
    :param remotefile: the path where to write the file on the remote server.
    """

    c = _get_connection(env.host_string)
    c.put(localfile, remotefile)


def read(remotefile) -> bytes:
    """Read the contents of a remote file.

    :param remotefile: the path of the remote file to read.

    This is useful when you just want to read the contents of a remote file without downloading it.
    """

    c = _get_connection(env.host_string)
    return c.read(remotefile)


def file_exists(remotefile) -> bool:
    """Check if a file exists on the remote server.

    :param remotefile: the path of the remote file that will be checked.
    """

    c = _get_connection(env.host_string)
    return c.file_exists(remotefile)


async def _local(command, environ=None, env_inherit=True, **kwargs) -> CommandResult:
    args = {
        "cwd": kwargs.get("cd"),
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.PIPE,
    }

    if env is not None:
        process_env = {}
        if env_inherit:
            process_env.update(os.environ)
        process_env.update(environ)
        args["env"] = environ

    label = "*local*"
    original_command = command
    cmdline = shlex.split(command)

    # https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.subprocess_exec
    # All other keyword arguments are passed to subprocess.Popen without interpretation, except for
    # bufsize, universal_newlines and shell, which should not be specified at all.
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


def local(command, cd=None, environ=None, env_inherit=True) -> CommandResult:
    """Execute `command` on the local machine.

    :param command: the command line string to execute.
    :param cd: the optional name of the directory where the command will be executed.
    :param environ: an optional dictionary containing environment variables to set when
    executing the command.
    :param env_inherit: set to `False` when you also specify `env` to execute the process in a new
    blank environment.
    """

    return run_in_loop(_local(command, cd=cd, environ=environ, env_inherit=env_inherit))


def run_concurrent(hosts, command, limit=0):
    """Execute `command` on `hosts` concurrently.

    :param hosts: a list of hosts where to run `command`.
    :param command: the command line string to execute.
    :param limit: limit the concurrent execution to `limit` hosts; set to `0` to execute on all the
    hosts at once.
    """

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
