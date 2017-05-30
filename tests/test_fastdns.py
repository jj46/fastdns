#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_fastdns
----------------------------------

Tests for `fastdns` module.
"""

import pytest
from contextlib import contextmanager
from fastdns import fastdns
import logging
import sys

logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p',
    )


def test_get_public_dns_servers():
    """Simple test of the public DNS server grabber
    """
    dns_servers = fastdns.get_public_dns_servers(countries=['us'])
    assert len(dns_servers) >= 100


def test_dns_resolver():
    """Simple test of the DNS resolver
    """
    hosts = ['www', 'mail', 'maps']
    dns_servers = ['8.8.8.8', '4.2.2.2']

    r = fastdns.Resolver(
        hostnames=hosts,
        domain='google.com',
        nameservers=dns_servers,
        tries=1
    )

    cache = r.resolve()
    assert len(cache[hosts[0]]) >= 1

    # Clear the resolver and try again
    r.clear()
    assert(len(r.cache) == 0)

    r.hostnames = hosts
    r.resolve()
    assert len(cache[hosts[1]]) >= 1
