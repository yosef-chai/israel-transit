"""Let the Home Assistant test harness import and run on Windows.

Home Assistant Core is not supported on Windows and imports two POSIX-only
modules unconditionally on the way in: ``homeassistant.runner`` imports
``fcntl``, and ``homeassistant.util.resource`` imports ``resource``. Neither is
reached by anything this integration does -- they belong to the supervisor
process that starts a real instance -- but the import alone stops
``pytest-homeassistant-custom-component`` from loading at all.

So they are stubbed, and only when they are genuinely absent: on Linux and
macOS this file does nothing. It has to be a plugin rather than a conftest
because the harness registers itself as a setuptools entry point, and those are
imported before any conftest is collected. ``pytest-ha.ini`` loads it with -p.

The second job is sockets. The harness blocks ``socket.socket`` outright and
allows only AF_UNIX through, because that is all asyncio needs on Linux. On
Windows asyncio builds its event loop over an AF_INET socketpair on the
loopback, so every test errors out before it starts. Sockets are put back here,
with the host allow-list left in place: a test can still build a loop, and a
real outbound request still fails the way it is meant to.

ponytail: stubs, not an emulation. If a test ever needs real file locking or a
real descriptor limit, that test wants a Linux runner, not a better stub.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest_socket

# What each module has to expose for the import chain to complete. The values
# are inert: nothing under test calls them.
_STUBS: dict[str, dict[str, Any]] = {
    "fcntl": {
        "LOCK_EX": 2,
        "LOCK_NB": 4,
        "LOCK_UN": 8,
        "flock": lambda *args, **kwargs: None,
        "fcntl": lambda *args, **kwargs: 0,
        "ioctl": lambda *args, **kwargs: 0,
    },
    "resource": {
        "RLIMIT_NOFILE": 7,
        "getrlimit": lambda *args, **kwargs: (1024, 4096),
        "setrlimit": lambda *args, **kwargs: None,
    },
}


def _install() -> None:
    for name, members in _STUBS.items():
        try:
            __import__(name)
        except ImportError:
            module = types.ModuleType(name)
            for attribute, value in members.items():
                setattr(module, attribute, value)
            sys.modules[name] = module


_install()


def pytest_runtest_setup() -> None:
    """Put sockets back after the harness has taken them away.

    Registered with -p, so this runs after the harness's own hook of the same
    name. Only on Windows: everywhere else its guard is correct as it stands.
    """
    if sys.platform != "win32":
        return
    pytest_socket.enable_socket()
    # Creating a socket is allowed again; reaching anything but the loopback
    # is still an error, which is the half of the guard that matters.
    pytest_socket.socket_allow_hosts(["127.0.0.1", "::1"])
