# 🦊 (Fox)

[![Build Status](https://travis-ci.org/piger/fox.svg?branch=master)](https://travis-ci.org/piger/fox)

🦊 (Fox) is an _experimental_ alternative implementation of _some_ of the
[Fabric 1.14](http://docs.fabfile.org/en/1.14/) APIs.

**NOTE**: this project is under development.

## Why?

I want to keep using the old Fabric 1.14 APIs with Python3:

- Fabric 2 changed the APIs
- Fabric3 (a fork of Fabric 1.14 for Python3) has some issues with Python3
- Maybe it's better to start from scratch with smaller project scope and focusing on Python3 only

## Example usage

Adapting code that uses Fabric 1.x should be easy enough, but some features will be missing and some
will behave differently.

``` python
from fox.conf import env
from fox.api import run, sudo

env.host_string = "server.example.com"
env.sudo_password = "very secret"

run("./configure --with-prefix=/90s", cd="/code/project")
sudo("make install", cd="/code/project")

# escaping should be handled correctly, for example:
run(
    """tail -n 1 < /etc/passwd | awk 'BEGIN { FS=":" } { print $1 " and " $3 }'"""
)
```

You can also use an explicit API:

``` python
from fox.connection import Connection
from fox.conf import env

env.sudo_password = "much more secret"
conn = Connection("app1.example.com")
conn.put("nginx.conf", "/tmp/nginx.conf")
# NOTE there is no "put() with sudo"
conn.sudo("mv /tmp/nginx.conf /etc/nginx/")
conn.sudo("systemctl restart nginx")
conn.disconnect()
```

You can also use Cluster mode when you want to run the same command on several hosts in parallel:

``` python
from fox.cluster import Cluster

cluster = Cluster("app1.example.com", "app2.example.com", "app3.example.com")
cluster.run("sleep $((1 + RANDOM % 5)) && hostname")
```

**NOTE** throttling still has to be implemented. All the commands will be run at once.
