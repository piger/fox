import shlex
import asyncio
import collections
from dataclasses import dataclass


@dataclass
class CommandResult:

    #: The command that was executed.
    command: str

    #: The actual command that was executed, including all the `cd` and `env` prefixes.
    actual_command: str

    #: The exit code of the executed command.
    exit_code: int

    #: The (partial) *stdout* output of the executed command.
    stdout: str

    #: The (partial) *stderr* output of the executed command.
    stderr: str

    #: The hostname of the server where the command was executed.
    hostname: str

    #: Wether the command was executed with sudo.
    sudo: bool = False

    # NOTE: when running in a pty there is no stderr!
    def summary(self):
        print(f'Ran command "{self.command}", exited with {self.exit_code}')


def shell_escape(cmdline: str) -> str:
    for char in ('"', "$", "`"):
        cmdline = cmdline.replace(char, "\\%s" % char)
    return cmdline


def prepare_environment(variables):
    """Prepare a `env` shell command to set up the requested process environment.

    NOTES:

    - an environment variable value can't reference another environment variable (e.g. you can't set
      FOO to "${USER}_foo".
    - due to how we chain commands together in Connection._run() we can't use the `env` command here
      because it doesn't allow you to do: env FOO="BAR" cd /baz
    """

    if not variables:
        return ""

    exports = []
    for key, value in variables.items():
        exports.append(f"{key}={shlex.quote(value)}")
    return f"export {' '.join(exports)} && "


def split_lines(data: str):
    """Separate newline terminated strings from the rest of the text

    Returns two values: the first is a list of newline terminated strings found in data, and the
    second value is any remaining text.

    TODO:
    - handle "\r"
    - handle "\r\n"
    """
    lines = []
    start = 0
    i = 0
    length = len(data)
    while True:
        try:
            i = data.index("\n", start)
        except ValueError:
            break
        line = data[start:i]
        line.rstrip("\r")
        lines.append(line)
        start = i + 1

    if start < length:
        return (lines, data[start:])

    return (lines, "")


def run_in_loop(future):
    """Run a co-routine in the default event loop"""

    try:
        result = asyncio.get_event_loop().run_until_complete(future)
    except Exception as ex:
        print("Exception: {}".format(ex))
        raise

    return result


async def read_from_stream(stream, writer, label, maxlen=10, decode=False, echo=True):
    buf = collections.deque(maxlen=maxlen)
    trail = ""

    while True:
        data = await stream.read(1024)
        if decode:
            data = data.decode("utf-8")
        if data == "":
            break

        buf.append(data)

        if trail:
            data = trail + data
            trail = ""

        lines, rest = split_lines(data)
        if echo:
            for line in lines:
                print(f"[{label}] {line}")

            if rest:
                trail += rest

    output = "".join(list(buf))
    return output


async def connect_streams(stream_in, stream_out):
    while True:
        buf = await stream_in.read(4096)
        if buf == "":
            break

        await stream_out.write(buf)
