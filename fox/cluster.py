import asyncio
import tqdm
import asyncssh
from .connection import _get_connection
from .utils import run_in_loop, CommandResult


async def _update_bar(bar, n, queue):
    for _ in range(n):
        await queue.get()
        queue.task_done()
        bar.update(1)

    bar.close()


class Cluster:
    """
    Cluster mode.

    Run a command on several hosts in parallel.

    TOOD:
    - canary run (do a canary run on the first host before doing the remanining)
    - exit after % of hosts failed
    """

    def __init__(self, *hosts):
        self.hosts = hosts
        self._connections = [_get_connection(host, use_cache=False) for host in self.hosts]

    def run(self, command, limit=0):
        return run_in_loop(self._run(command, limit))

    async def _run(self, command, limit=0):
        bar = tqdm.tqdm(total=len(self.hosts))
        qbar = asyncio.Queue()
        futures_done = []
        aws = set()

        bar_task = asyncio.ensure_future(_update_bar(bar, len(self.hosts), qbar))

        for connection in self._connections:
            aws.add(asyncio.ensure_future(self._do(qbar, connection, command)))
            if limit and len(aws) >= limit:
                done, pending = await asyncio.wait(aws, return_when=asyncio.FIRST_COMPLETED)
                aws = pending
                futures_done.extend(done)

        if len(aws):
            done, pending = await asyncio.wait(aws, return_when=asyncio.ALL_COMPLETED)
            futures_done.extend(done)

        _ = await asyncio.wait({bar_task})

        results = [future.result() for future in futures_done]
        for connection, result in results:
            if isinstance(result, CommandResult):
                print(f"output from {connection.nickname}: {result.stdout}", end="")
            else:
                print(f"command failed on {connection.nickname}: {result}")

        return results

    async def _do(self, queue, connection, command):
        try:
            result = await connection._run(command, echo=False)
        except Exception as exc:
            print(f"Task on {connection} failed: {exc}")
            result = None

        await queue.put(1)
        return (connection, result)


def connect_pipes(source, source_command, destination, destination_command):
    """Connects processes on two connections with a pipe

    Pipe stdout and stderr from a command executed on a source connection to stdin of a process on a
    destination connection.
    """
    return run_in_loop(_connect_pipes(source, source_command, destination, destination_command))


async def _connect_pipes(source, source_command, destination, destination_command):
    source_conn = _get_connection(source, use_cache=False)
    dest_conn = _get_connection(destination, use_cache=False)

    await asyncio.gather(source_conn._connect(), dest_conn._connect())

    async with source_conn._connection.create_process(
        source_command, stderr=asyncssh.STDOUT
    ) as source_proc, dest_conn._connection.create_process(
        destination_command, stdin=source_proc.stdout
    ) as dest_proc:
        stdout, stderr = await asyncio.gather(
            dest_conn._read_from(dest_proc.stdout, dest_proc.stdin),
            dest_conn._read_from(dest_proc.stderr, dest_proc.stdin),
        )

    return CommandResult(
        command=destination_command,
        actual_command=destination_command,
        exit_code=dest_proc.exit_status,
        stdout=stdout,
        stderr=stderr,
        hostname=destination,
    )
