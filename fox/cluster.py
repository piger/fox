import asyncio
import tqdm
from .connection import Connection, _get_connection
from .utils import run_in_loop


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
        results = []
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
