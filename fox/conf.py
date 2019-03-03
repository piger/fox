import os
from collections.abc import MutableMapping
from typing import Any
from .sshconfig import SSHConfig


class Environment(MutableMapping):
    def __init__(self, *args, **kwargs):
        self._storage = dict(*args, **kwargs)

    def __getitem__(self, key: str) -> Any:
        return self._storage[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._storage[key] = value

    def __delitem__(self, key):
        del self._storage[key]

    def __iter__(self):
        return iter(self._storage)

    def __len__(self) -> int:
        return len(self._storage)

    def __getattr__(self, key) -> Any:
        if key in self._storage:
            return self._storage[key]

        raise NotImplementedError()


env = Environment(
    {
        "host_string": None,
        "term_type": "vt100",
        "term_size": (80, 24),
        "use_ssh_config": True,
        "ssh_config_path": os.path.expanduser("~/.ssh/config"),
        "sudo_password": None,
        "sudo_prompt": "sudo password:",
        "username": None,
        "port": None,
        "private_key": None,
    }
)


_ssh_config = None


def options_to_connect(hostname):
    """Returns all the SSH options needed to connect to `hostname`"""

    # these options will override the ones from ssh_config
    options_from_env = {"hostname": hostname}
    # NOTE: ssh_config use the "User" word instead of "Username"!
    if env.username is not None:
        options_from_env["user"] = env.username
    if env.port is not None:
        options_from_env["port"] = env.port
    if env.private_key is not None:
        options_from_env["identityfile"] = env.private_key

    if not env.use_ssh_config:
        return options_from_env

    global _ssh_config
    if _ssh_config is None:
        _ssh_config = SSHConfig()
        _ssh_config.load(os.path.abspath(env.ssh_config_path))

    ssh_options = _ssh_config.lookup(hostname)

    # NOTE: we're updateing ssh_options with whatever was specified in `env`. By default all the
    # `env` variables that can affect this configuration are set to `None`.
    ssh_options.update(options_from_env)

    return ssh_options
