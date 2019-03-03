import os
from typing import Dict, Any, Optional
from .sshconfig import SSHConfig


class Environment:

    #: The hostname of the remote server that will be used in all of the `run()`, `sudo()`
    #: and all of the other remote commands.
    host_string: Optional[str] = None

    #: The terminal type to emulate when a *pty* is requested.
    term_type = "vt100"

    #: The size of the emulated terminal when a *pty* is requested.
    term_size = (80, 24)

    #: Set to `True` to enable the loading of `~/.ssh/config`.
    use_ssh_config = True

    #: Set to `True` to respect the contents of `~/.ssh/known_hosts` and enable the fingerprint
    # verification.
    use_known_hosts = True

    #: Set the path to the OpenSSH configuration file.
    ssh_config_path = os.path.expanduser("~/.ssh/config")

    #: Set the password for the `sudo()` commands.
    sudo_password: Optional[str] = None

    #: The prompt for sudo commands (do not change!).
    sudo_prompt = "sudo password:"

    #: The remote username.
    username: Optional[str] = None

    #: The remote port.
    port: Optional[int] = None

    #: The path to a OpenSSH private key.
    private_key: Optional[str] = None


#: Global configuration object.
env = Environment()

_ssh_config: Optional[SSHConfig] = None


def options_to_connect(hostname: str) -> Dict[str, Any]:
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
