# -*- coding: utf-8 -*-
"""
resolver.py - A fast multi-threaded DNS resolver using the dnspython library

Examples:
    # Importing the library
    # from fastdns import fastdns

    # Resolving many DNS hosts
    # >>> from pprint import pprint
    # >>> r = fastdns.Resolver(domain='cisco.com')
    # >>> r.hostnames = {'www', 'wwwin', 'ds', 'release'}
    # >>> cache = r.resolve()
    # >>> pprint(cache)
    # {'ds': {'171.71.198.38',
    #         '173.36.12.198',
    #         '173.36.129.230',
    #         '173.37.248.6',
    #         '64.100.37.70'},
    #  'release': {'173.36.64.40', '173.37.253.56'},
    #  'www': {'173.37.145.84', '72.163.4.161'},
    #  'wwwin': {'173.36.27.110', '173.37.111.50'}}

    # Resolving mixed hostnames and IPs (v4 and v6)
    # >>> hostnames = {'www', '2001:420:210d::a', '8.8.8.8', 'www.purple.com'}
    # >>> cache = fastdns.Resolver(hostnames=hostnames, domain='cisco.com').resolve()
    # >>> pprint(cache)
    # {'dns-rtp': {'2001:420:210d::a'},
    #  'google-public-dns-a.google.com': {'8.8.8.8'},
    #  'www': {'173.37.145.84', '72.163.4.161'},
    #  'www.purple.com': {'153.104.63.227'}}

    # Performing a single DNS lookup
    # >>> fastdns.dns_lookup('wwwin')
    # ['173.37.111.50']

    # Performing a single reverse lookup
    # >>> fastdns.reverse_lookup('8.8.8.8')
    # 'google-public-dns-a.google.com'
"""
from queue import Queue
from multiprocessing import Lock
from threading import Thread
import logging
import sys
import re
from ipaddress import ip_address
import traceback
import dns.resolver
import dns.exception
import dns.reversename
import requests

logging.getLogger(__name__).addHandler(logging.NullHandler())


def get_public_dns_servers(ipv6=False, max_per_country=100, countries=['us', 'gb']):
    """
    Get DNS servers from https://public-dns.info/nameserver/<country_code>.txt
    
    Args:
        ipv6 (bool): Use ipv6
        max_per_country (int): Maximum DNS servers per country to use (Default: 100)
        countries (list): List of country codes to get DNS servers from (Default: ['us', 'gb'])

    Returns:
        set: DNS server IP addresses
    """
    logging.info('Getting public DNS servers')

    servers = set()

    for c in countries:
        try:
            r = requests.get('https://public-dns.info/nameserver/{0}.txt'.format(c))
            _servers = sorted(list(set(r.text.split())))
            logging.debug('Got {0} servers for country code "{1}"'.format(len(_servers), c))
            _servers = _servers[:max_per_country]
        except:
            logging.error('Unable to retrieve DNS servers for country "{0}"'.format(c))
            continue

        if ipv6:
            for server in _servers:
                try:
                    ip = ip_address(server)
                    servers.add(str(ip))
                except:
                    logging.error('Invalid IP: {0}'.format(server))
                    continue

        else:
            for server in _servers:
                try:
                    ip = ip_address(server)
                    if ip.version != 6:
                        servers.add(str(ip))
                except:
                    logging.error('Invalid IP: {0}'.format(server))
                    continue

    logging.info('Got {0} public DNS servers'.format(len(servers)))

    return servers


def without_domain(host, domain):
    """
    Remove domain from a host

    Args:
        host (str): hostname
        domain (str): dns domain

    Returns:
        host (str): hostname without domain

    Examples:
        >>> without_domain('www.google.com', 'google.com')
        'www'
    """
    if host.endswith(domain):
        return re.sub(re.escape(domain) + r'$', '', host)
    else:
        return host


def reverse_lookup(ip, server=None):
    """
    Perform a reverse lookup on an `ip` with a given DNS `server`

    Args:
        ip (str): IP address of host
        server (str): IP addres of DNS server

    Returns:
        str: hostname if found, None otherwise
    """
    if server is not None:
        r = dns.resolver.Resolver(configure=False)
        r.nameservers = [server]
    else:
        r = dns.resolver.Resolver()

    try:
        dns_name = dns.reversename.from_address(ip)
        a = re.sub('\.$', '', r.query(dns_name, "PTR")[0].to_text())
        logging.debug('Reverse lookup for IP {0} using server {1} found name: {2}'.format(ip, server, a))
        return a
    except:
        logging.debug('Reverse lookup for {0} using server {1} failed.'.format(ip, server))
        logging.error(traceback.format_exc())
        return None


def dns_lookup(hostname, server=None, timeout=3, domain=None):
    """
    Resolve a `hostname` using a given DNS `server`

    Args:
        hostname (str): host to be resolved
        server (str): IP address of DNS server
        timeout (int): DNS timeout in seconds
        domain (str): Domain name ('cisco.com')

    Returns:
        IP addresses (list): List of IP addresses (str) or None
    """
    if server is not None:
        r = dns.resolver.Resolver(configure=False)
        r.nameservers = [server]
    else:
        r = dns.resolver.Resolver()

    r.lifetime = timeout
    if domain:
        r.domain = dns.name.from_text(domain)

    try:
        answers = r.query(hostname, 'A')
    except:
        logging.error(traceback.format_exc())
        return None

    ips = set(a.to_text() for a in answers)
    logging.debug('DNS lookup for {0} using server {1} found IPs: {2}'.format(hostname, server, ', '.join(ips)))
    return ips


class Resolver:
    def __init__(self, **kwargs):
        """
        A fast DNS resolver

        Args:
            hostnames (set): Hostnames to perform DNS resolutions (or reverse lookups for IPs)
            domain (str): DNS domain
            timeout (int): DNS timeout
            tries (int): number of DNS resolution attempts to try
            nameservers (list): DNS name servers to query
        """
        self.tries = kwargs.get('tries', 1)
        self.timeout = kwargs.get('timeout', 5)
        self.hostnames = kwargs.get('hostnames', ['www.google.com', 'www.cisco.com'])
        self.domain = kwargs.get('domain', 'google.com')
        self.nameservers = kwargs.get('nameservers', ['8.8.8.8', '8.8.4.4'])

        self.cache = dict()
        self.q = None
        self.workers = None

    def clear(self, cache=True):
        self.hostnames = []
        if cache:
            self.cache = dict()
        self.q = None
        self.workers = None

    def _run(self, q, lock):
        """
        Run the DNS resolutions that have been queued until the queue is empty.  
        Update the DNS cache as hosts are resolved.

        Args:
            q (Queue.queue): Queue  
        """
        while True:
            host, server = q.get()

            ips = dns_lookup(host, server, domain=self.domain, timeout=self.timeout)
            if ips:
                self._update_cache(host, ips, lock)
            else:
                self._update_cache(host, set(), lock)
            q.task_done()

    def _update_cache(self, host, ips, lock):
        """
        Updates the DNS cache for `host`, adding `ips` (does not remove IPs from existing cache).

        Uses a lock to allow threads to update the cache

        Args:
            host (str): Hostname in the DNS cache 
            ips (set): Set of IP addresses (str)
        """
        # logging.debug('Waiting for lock')
        lock.acquire()
        try:
            # logging.debug('Acquired lock')
            if ips:
                if host not in self.cache:
                    self.cache[host] = set()
                elif self.cache[host] is None:
                    self.cache[host] = set()

                for ip in ips:
                    if ip is not None:
                        self.cache[host].add(ip)
            else:
                if host not in self.cache:
                    self.cache[host] = set()
        finally:
            lock.release()

    def _create_workers(self, q, lock, num_workers):
        """
        Create a Queue of workers for the DNS lookup operations

        Args:
            num_workers (int): number of threads to spawn 
        """
        logging.info('Creating {0} workers'.format(num_workers))
        for i in range(num_workers):
            worker = Thread(target=self._run, args=(q, lock), name='worker-{}'.format(i))
            worker.setDaemon(True)
            worker.start()

        for i in range(self.tries):
            for host in self.hostnames:
                for server in self.nameservers:
                    q.put((host, server))

    def _process_dead_hosts(self):
        """
        Process dead hosts in the cache

        Returns:
            set: self.dead_hosts
        """
        self.dead_hosts = {h for h, ips in self.cache.items() if not ips}
        return self.dead_hosts

    def resolve(self):
        """
        Resolve all of the hosts in `self.hostnames`, storing the results in `self.cache`

        Returns:
            dict: self.cache
        """
        lock = Lock()
        max_workers = 510
        num_queries = len(self.hostnames) * self.tries * len(self.nameservers)

        if not self.workers:
            q = Queue(maxsize=0)

            if self.hostnames:
                if num_queries > max_workers:
                    self._create_workers(q, lock, max_workers)
                else:
                    self._create_workers(q, lock, num_queries)
            else:
                self._create_workers(q, lock, max_workers)

            self.workers = True
            self.q = q

            logging.info('Performing {0} DNS lookups'.format(num_queries))

        try:
            self.q.join()
        except KeyboardInterrupt:
            sys.exit(1)

        self._process_dead_hosts()
        # self._process_external_hosts()

        return self.cache
