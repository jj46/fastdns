=======
fastdns
=======
The purpose of this library is to use multiple DNS queries to multiple DNS servers to cache as many IPs as possible for DNS hosts that return lots of IP addresses (cloud hosted).

* Free software: MIT license

Features
--------
* DNS Resolver library for performing many DNS queries
* DNS Caching library for caching hosts with many IPs

Note: If you are looking to simply determine if a host is resolvable or don't care as much about hosts with tons of IPs, the berserker resolver may suit your needs better -> https://github.com/DmitryFillo/berserker_resolver

Installation
------------
    git clone https://github.com/jj46/fastdns.git
    cd fastdns
    python3 -m pip install -e .

Usage
-----
    >>> from fastdns import resolver
    >>> from pprint import pprint
    >>> r = resolver.Resolver(
        hostnames=['www', 'mail', 'maps'],
        domain='google.com',
        nameservers=['8.8.8.8', '4.2.2.2'],
        tries=1
        )
    >>> pprint(r.resolve())
    'mail': {'172.217.8.5', '216.58.217.69', '172.217.7.229', '172.217.5.229'},
    'maps': {'172.217.11.46',
             '172.217.5.238',
             '172.217.7.142',
             '172.217.7.238',
             '216.58.217.142',
             '216.58.217.174'},
    'www': {'216.58.217.68', '216.58.217.132', '172.217.7.228', '172.217.7.196'}}

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
