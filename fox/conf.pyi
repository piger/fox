from typing import Tuple, Optional, Dict, Any
from .sshconfig import SSHConfig

class Environment:
    host_string: str
    term_type: str
    term_size: Tuple[int, int]
    use_ssh_config: bool
    use_known_hosts: bool
    ssh_config_path: str
    sudo_password: Optional[str]
    sudo_prompt: str
    username: str
    port: int
    private_key: str

env: Environment

_ssh_config: Optional[SSHConfig]

def options_to_connect(hostname: str) -> Dict[str, Any]: ...
