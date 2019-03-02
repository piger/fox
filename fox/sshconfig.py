import re
import os
import socket
import getpass
from fnmatch import fnmatch


class Error(Exception):
    pass


SSH_EXPAND_OPTIONS = ["proxycommand", "controlpath"]


def match(hostname, patterns):
    for pattern in patterns:
        if pattern.startswith("!"):
            negate = True
            pattern = pattern[1:]
        else:
            negate = False

        if fnmatch(hostname, pattern):
            if negate:
                return False
            return True

    return False


# not all SSH options support all the available tokens, but whatever...
def expand_tokens(s, nickname, options):
    if "%%" in s:
        s = s.replace("%%", "%")
    if "$d" in s:
        s = s.replace("%d", os.path.expanduser("~"))
    if "%h" in s:
        s = s.replace("%h", options["hostname"])
    if "%i" in s:
        s = s.replace("%i", str(os.getuid()))
    if "%L" in s:
        s = s.replace("%L", socket.gethostname())
    if "%l" in s:
        s = s.replace("%l", socket.getfqdn())
    if "%n" in s:
        # The original remote hostname, as given on the command line.
        s = s.replace("%n", nickname)
    if "%p" in s:
        s = s.replace("%p", str(options["port"]))
    if "%r" in s:
        s = s.replace("%r", options["user"])
    if "%u" in s:
        s = s.replace("%u", getpass.getuser())
    return s


class SSHOptions:
    def __init__(self, patterns, **options):
        self.patterns = patterns.copy()
        self.options = {}
        for key, value in options.items():
            self.options[key] = value

    def set_option(self, key, value):
        self.options[key] = value


class SSHConfig:
    def __init__(self):
        self.blocks = []

    def load(self, filename):
        with open(filename) as fd:
            sshopt = None

            for line in fd:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                m = re.search(r"^host +(.*)$", line, re.I)
                if m:
                    if sshopt is not None:
                        self.blocks.append(sshopt)
                    patterns = [p.strip() for p in m.group(1).split(",")]
                    sshopt = SSHOptions(patterns)
                    continue

                if sshopt is None:
                    raise Error("Error: expected to be in a 'Host' block!")
                key, value = line.split(" ", 1)
                key = key.lower()
                sshopt.set_option(key, value)

            if sshopt is not None:
                self.blocks.append(sshopt)

    def lookup(self, nickname):
        options = {}

        for block in self.blocks:
            if match(nickname, block.patterns):
                for opt_name, opt_value in block.options.items():
                    if opt_name not in options:
                        options[opt_name] = opt_value

        if "hostname" not in options:
            options["hostname"] = nickname
        if "port" not in options:
            options["port"] = 22
        if "user" not in options:
            options["user"] = getpass.getuser()

        for opt in SSH_EXPAND_OPTIONS:
            if opt in options:
                options[opt] = expand_tokens(options[opt], nickname, options)

        for key in options:
            # if the value starts with ~ assume it's a path and expand it
            if isinstance(options[key], str) and options[key].startswith("~"):
                options[key] = os.path.expanduser(options[key])

            if key == "port":
                options[key] = int(options[key])

        return options
