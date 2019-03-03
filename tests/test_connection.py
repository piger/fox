import asyncio
import asyncssh
import pytest
from fox.conf import env
from fox.api import run
from fox.connection import Connection
from fox.utils import run_in_loop


SSH_SERVER_PORT = 30123


@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


class SSHServer(asyncssh.SSHServer):
    def begin_auth(self, username):
        # no auth required
        return False

    def public_key_auth_supported(self):
        return True


async def _test_run_command():
    def _server_factory():
        return SSHServer()

    capture = {}

    def _process_factory(process):
        process.stderr.close()
        process.stdout.close()
        capture["command"] = process.command
        process.exit(0)

    key = asyncssh.generate_private_key("ssh-rsa")
    pubkey = key.convert_to_public()

    server_key = asyncssh.generate_private_key("ssh-rsa")
    server_pubkey = server_key.convert_to_public()

    server = await asyncssh.create_server(
        _server_factory, host="127.0.0.1", port=SSH_SERVER_PORT, server_host_keys=[server_key],
        process_factory=_process_factory,
    )

    env.use_ssh_config = False
    conn = Connection("localhost", "pippo", SSH_SERVER_PORT,
                      private_key=key)
    result = await conn._run("uname -a", cd="/tmp")
    assert capture["command"] == """cd "/tmp" && uname -a"""
    server.close()


def test_run_command(event_loop):
    event_loop.run_until_complete(_test_run_command())
