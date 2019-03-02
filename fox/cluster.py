import asyncio
import tqdm
from .connection import _get_connection
from .utils import run_in_loop, CommandResult


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

    def run(self, command):
        return run_in_loop(self._run(command))

    async def _run(self, command):
        bar = tqdm.tqdm(total=len(self.hosts))
        qresults = asyncio.Queue()

        result = await asyncio.gather(
            *[self._do(qresults, connection, command) for connection in self._connections],
            self._update_bar(bar, len(self.hosts), qresults)
        )

        command_outputs = result[-1]
        for connection, output in command_outputs:
            print(f"output from {connection}: {output.stdout}", end='')

    async def _do(self, queue, connection, command):
        try:
            result = await connection._run(command, echo=False)
        except Exception as exc:
            print(f"task on {connection} failed: {exc}")
            await queue.put((connection, None))
        else:
            await queue.put((connection, result))

    async def _update_bar(self, bar, n, queue):
        results = []

        for _ in range(n):
            result = await queue.get()
            results.append(result)
            queue.task_done()
            bar.update(1)

        bar.close()

        return results


def connect_pipes(source, source_command, destination, destination_command):
    return run_in_loop(_connect_pipes(source, source_command, destination, destination_command))


async def _connect_pipes(source, source_command, destination, destination_command):
    source_conn = _get_connection(source, use_cache=False)
    dest_conn = _get_connection(destination, use_cache=False)
    await source_conn._connect()
    await dest_conn._connect()

    async with source_conn._connection.create_process(source_command) as source_proc, dest_conn._connection.create_process(destination_command, stdin=source_proc.stdout) as dest_proc:
        stdout, stderr = await asyncio.gather(
            dest_conn._read_from(dest_proc.stdout, dest_proc.stdin, echo=True),
            dest_conn._read_from(dest_proc.stderr, dest_proc.stdin, echo=True),
        )

    return CommandResult(
        command=command,
        exit_code=dest_proc.exit_status,
        stdout=stdout,
        stderr=stderr,
    )
