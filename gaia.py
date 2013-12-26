"""Python ctypes implementation of getaddrinfo_a.

This wraps the GNU libc implementation of getaddrinfo_a, with a simple
interface. The module exports a single function, get_records, which looks up
multiple DNS names in parallel.

Again, this will only work on systems whose libc implementation is glibc, and
it will probably only work on Linux systems (since the sonames are hardcoded).

This code is based on the example code in the getaddrinfo_a man page, and is
released to the public domain.
"""

import ctypes


libc = ctypes.cdll.LoadLibrary('libc.so.6')
libanl = ctypes.cdll.LoadLibrary('libanl.so.1')


# these constants cribbed from libanl
GAI_WAIT = 0
GAI_NOWAIT = 1
NI_MAXHOST = 1025
NI_NUMERICHOST = 1


class addrinfo(ctypes.Structure):
    _fields_ = [('ai_flags', ctypes.c_int),
                ('ai_family', ctypes.c_int),
                ('ai_socktype', ctypes.c_int),
                ('ai_protocol', ctypes.c_int),
                ('ai_addrlen', ctypes.c_size_t),
                ('ai_addr', ctypes.c_void_p),
                ('ai_canonname', ctypes.c_char_p),
                ('ai_next', ctypes.c_void_p)]


c_addrinfo_p = ctypes.POINTER(addrinfo)


class gaicb(ctypes.Structure):
    _fields_ = [('ar_name', ctypes.c_char_p),
                ('ar_service', ctypes.c_char_p),
                ('ar_request', c_addrinfo_p),
                ('ar_result', c_addrinfo_p)]


c_gaicb_p = ctypes.POINTER(gaicb)


getaddrinfo_a = libanl.getaddrinfo_a
getaddrinfo_a.argtypes = [ctypes.c_int,   # mode
                          ctypes.POINTER(c_gaicb_p), # list
                          ctypes.c_int,   # nitems
                          ctypes.c_void_p # sevp
                          ]
getaddrinfo_a.restype = ctypes.c_int


getnameinfo = libc.getnameinfo
getnameinfo.argtypes = [ctypes.c_void_p, # sa
                        ctypes.c_size_t, # salen
                        ctypes.c_char_p, # host
                        ctypes.c_size_t, # hostlen
                        ctypes.c_char_p, # serv
                        ctypes.c_size_t, # servlen
                        ctypes.c_int     # flags
                        ]
getnameinfo.restype = ctypes.c_int


# statically allocate the host array
host = ctypes.cast((ctypes.c_char * NI_MAXHOST)(), ctypes.c_char_p)


def get_records(names):
    """Get multiple A records, in parallel.

    Args:
      names - a list of names to lookup

    Returns:
      dictionary mapping lookup names to IP addresses
    """
    result = {}

    # set up the array of gaicb pointers
    reqs = (c_gaicb_p * len(names))()
    for i, name in enumerate(names):
        g = gaicb()
        ctypes.memset(ctypes.byref(g), 0, ctypes.sizeof(gaicb))
        g.ar_name = name
        reqs[i] = ctypes.pointer(g)

    # get the records; this does i/o and blocks
    ret = getaddrinfo_a(GAI_WAIT, reqs, len(names), None)
    assert ret == 0

    # parse the records out of all the structs
    for req in reqs:
        name = req.contents.ar_name
        res = req.contents.ar_result.contents
        ret = getnameinfo(res.ai_addr, res.ai_addrlen,
                          host, NI_MAXHOST, None, 0, NI_NUMERICHOST)
        assert ret == 0
        result[name] = host.value

    return result


__all__ = ['get_records']


if __name__ == '__main__':
    print get_records(['eklitzke.org', 'google.com'])
