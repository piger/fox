import asyncio
import asyncssh
import pytest
from fox.conf import env
from fox.api import run
from fox.connection import Connection
from fox.utils import run_in_loop


SSH_SERVER_PORT = 30123


class SSHServer(asyncssh.SSHServer):
    def begin_auth(self, username):
        # no auth required
        return False

    def public_key_auth_supported(self):
        return True


def make_process_factory():
    capture = {}

    def _process_factory(process):
        process.stderr.close()
        process.stdout.close()
        capture["command"] = process.command
        process.exit(0)

    return capture, _process_factory


def server_factory():
    return SSHServer()


@pytest.mark.asyncio
async def test_run_command():
    capture, process_factory = make_process_factory()

    key = asyncssh.generate_private_key("ssh-rsa")
    server_key = asyncssh.generate_private_key("ssh-rsa")

    server = await asyncssh.create_server(
        server_factory,
        host="127.0.0.1",
        port=SSH_SERVER_PORT,
        server_host_keys=[server_key],
        process_factory=process_factory,
    )

    env.use_ssh_config = False
    env.use_known_hosts = False
    conn = Connection("localhost", "pippo", SSH_SERVER_PORT, private_key=key)
    result = await conn._run("uname -a", cd="/tmp")
    assert capture["command"] == """cd "/tmp" && uname -a"""
    server.close()
    return True
