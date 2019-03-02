import os
import shlex
import getpass
import warnings
import asyncio
import logging
import collections
import atexit
import tqdm
import asyncssh
from .conf import env, options_to_connect
from .utils import run_in_loop, CommandResult, prepare_environment


# disable annoying warnings (we can't fix the problems in 3rd party libs)
warnings.simplefilter("ignore")


log = logging.getLogger(__name__)

# A cache of Connection objects indexed by *name* (not hostname!). We only cache connections creates
# with the global run() and sudo() methods. Maybe the tunnels too?
_connections_cache = {}


def _clean_connections():
    # would be better to close them all at once with gather() or similar
    for hostname, conn in _connections_cache.items():
        if conn.connected:
            log.info(f"Cleaning up connection for {hostname}")
            conn.disconnect()


atexit.register(_clean_connections)


class Connection:
    """
    A SSH connection to a remote server.

    What do we need to connect to a server:
    - hostname
    - port (optional)
    - username (optional, defaults to local user)
    - password (optional)
    - private key (optional)
    - path to agent (asyncssh read "$SSH_AUTH_SOCK" by default)
    - ProxyJump or ProxyCommand (!!!)
    """
    def __init__(self, hostname, username, port, private_key=None, password=None, agent_path=None,
                 tunnel=None, nickname=None):
        self.hostname = hostname
        self.username = username
        self.port = port
        self.private_key = private_key
        self.password = password
        self.agent_path = agent_path
        self.tunnel = tunnel
        if nickname:
            self.nickname = nickname
        else:
            self.nickname = self.hostname
        self._connection = None
        self._sftp_client = None

    async def _read_from(self, stream, writer, maxlen=10, echo=True) -> str:
        buf = collections.deque(maxlen=maxlen)

        while True:
            data = await stream.read(1024)
            if data == "":
                break

            buf.append(data)
            if echo:
                print(data, end="")
            if data.endswith("sudo password:"):
                if env.sudo_password is None:
                    env.sudo_password = getpass.getpass("Need password for sudo: ")
                writer.write(f"{env.sudo_password}\n")

        output = "".join(list(buf))
        return output

    async def _run(self, command, sudo=False, cd=None, pty=False, environ=None, echo=True,
                   **kwargs) -> CommandResult:
        """Run a shell command on the remote host"""

        if self._connection is None:
            await self._connect()

        if cd:
            command = 'cd "{}" && {}'.format(cd, command)

        env_command = prepare_environment(environ)
        # XXX
        log.debug(f"env_command = {env_command}")

        if sudo:
            command = f"{env_command}{command}"
            command = f'sudo -S -p {shlex.quote(env.sudo_prompt)} $SHELL -c {shlex.quote(command)}'
        else:
            command = f"{env_command}{command}"

        # XXX
        log.debug(f"command = {command}")

        args = {}
        if pty:
            args.update({
                "term_type": env.term_type,
                "term_size": env.term_size,
            })

        async with self._connection.create_process(command, **args) as proc:
            stdout, stderr = await asyncio.gather(
                self._read_from(proc.stdout, proc.stdin, echo=echo),
                self._read_from(proc.stderr, proc.stdin, echo=echo),
            )

        return CommandResult(
            command=command,
            exit_code=proc.exit_status,
            stdout=stdout,
            # if we use a pty this will be empty
            stderr=stderr,
        )

    # use the event loop
    def run(self, command, pty=True, cd=None, environ=None) -> CommandResult:
        kwargs = {
            "pty": pty,
            "cd": cd,
            "environ": environ,
        }
        return run_in_loop(self._run(command, **kwargs))

    # use the event loop
    def sudo(self, command, pty=True, cd=None, environ=None) -> CommandResult:
        kwargs = {
            "pty": pty,
            "cd": cd,
            "sudo": True,
            "environ": environ,
        }
        return run_in_loop(self._run(command, **kwargs))

    async def _connect(self):
        log.info(f"Connecting to {self.hostname}")

        args = {
            "username": self.username,
        }

        if self.tunnel:
            log.info(f"Connecting to tunnel {self.tunnel}")
            tunnel_conn = _get_connection(self.tunnel, use_cache=False)
            await tunnel_conn._connect()
            args["tunnel"] = tunnel_conn

        # we either use the private key OR the agent; loading the private key might fail while the
        # agent could still be working.
        if self.agent_path:
            args["agent_path"] = self.agent_path
        elif self.private_key:
            args["client_keys"] = [self.private_key]

        self._connection = await asyncssh.connect(
            self.hostname, self.port, **args
        )

    # use the event loop
    def disconnect(self):
        # Maybe here we should also delete ourself from the connection cache, but we don't know our
        # own "nickname"!
        if self._connection is not None:
            self._connection.close()
            run_in_loop(self._connection.wait_closed())
        self._connection = None
        print("disconnected")

    @property
    def connected(self) -> bool:
        return self._connection is not None

    async def get_sftp_client(self) -> asyncssh.SFTPClient:
        if self._connection is None:
            await self._connect()

        if self._sftp_client is None:
            self._sftp_client = await self._connection.start_sftp_client()
        return self._sftp_client

    async def _get(self, remotefile, localfile):
        sftp_client = await self.get_sftp_client()

        try:
            # do something with `progress_handler` to show a progress bar
            size = await sftp_client.getsize(remotefile)

            # from https://asyncssh.readthedocs.io/en/latest/api.html#asyncssh.SFTPClient.get
            block_size = 16384

            i = size // block_size + 1
            if i < 0:
                i = 1
            bar = tqdm.tqdm(total=i, desc=os.path.basename(remotefile))

            def _update_bar(source, dest, cur, tot):
                bar.update(1)

            await sftp_client.get(
                remotefile,
                localfile,
                progress_handler=_update_bar,
                block_size=block_size
            )
            bar.close()

        except (OSError, asyncssh.SFTPError):
            raise

    # use the event loop
    def get(self, remotefile, localfile):
        run_in_loop(self._get(remotefile, localfile))

    async def _read(self, remotefile) -> bytes:
        sftp_client = await self.get_sftp_client()

        try:
            size = await sftp_client.getsize(remotefile)
            bar = tqdm.tqdm(total=size, desc=os.path.basename(remotefile))

            fd = await sftp_client.open(remotefile, "rb")
            data = []
            while True:
                # 16384 is the default block size
                buf = await fd.read(16384)
                if buf == b"":
                    break
                data.append(buf)
                bar.update(len(buf))

            fd.close()
            bar.close()

            return b"".join(data)
        except (OSError, asyncssh.SFTPError):
            raise

    # use the event loop
    def read(self, remotefile) -> bytes:
        return run_in_loop(self._read(remotefile))

    async def _put(self, localfile, remotefile):
        sftp_client = await self.get_sftp_client()

        try:
            size = os.path.getsize(localfile)

            # from https://asyncssh.readthedocs.io/en/latest/api.html#asyncssh.SFTPClient.get
            block_size = 16384

            i = size // block_size + 1
            if i < 0:
                i = 1
            bar = tqdm.tqdm(total=i, desc=os.path.basename(localfile))

            def _update_bar(source, dest, cur, tot):
                bar.update(1)

            await sftp_client.put(
                localfile,
                remotefile,
                progress_handler=_update_bar,
                block_size=block_size
            )
            bar.close()

        except (OSError, asyncssh.SFTPError):
            raise

    # use the event loop
    def put(self, localfile, remotefile):
        run_in_loop(self._put(localfile, remotefile))

    async def _file_exists(self, remotefile) -> bool:
        sftp_client = await self.get_sftp_client()
        return await sftp_client.exists(remotefile)

    # use the event loop
    def file_exists(self, remotefile):
        return run_in_loop(self._file_exists(remotefile))


def _get_connection(name=None, use_cache=True):
    """Get a connection for `name`.

    `name` does not need to be a FQDN; it can be a "nickname" from a SSH configuration file.
    """

    global _connections_cache

    if name is None and env.host_string is None:
        raise RuntimeError("env.host_string is empty!")

    if name is None:
        name = env.host_string

    if use_cache and name in _connections_cache:
        conn = _connections_cache[name]
        # here we delete stale Connections objects.
        if conn.connected:
            return conn
        del _connections_cache[name]

    ssh_options = options_to_connect(name)

    args = {}
    if "identityfile" in ssh_options:
        args["private_key"] = ssh_options["identityfile"]
    if "identityagent" in ssh_options:
        args["agent_path"] = ssh_options["identityagent"]
    # TODO:
    # identitiesonly yes

    # NOTE: we only cache connections created here, and maybe the tunnels.
    # maybe by default we should not re-use the tunnels, as the default behavior of SSH
    c = Connection(ssh_options["hostname"], ssh_options["user"], ssh_options["port"], **args)
    if use_cache:
        _connections_cache[name] = c
    return c
