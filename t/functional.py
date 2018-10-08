'Functional Tests'

import os, re, pytest
from subprocess import Popen, PIPE
from twisted.internet import protocol

####################################################################
#   Framework for testing with Twisted

@pytest.fixture
def reactor():
    timeout_secs = 3
    #   We want a reactor that works on all platforms.
    from twisted.internet.selectreactor import SelectReactor
    r = SelectReactor()
    d = { 'forced': False }     # No `nonlocal` in Python 2
    def force_stop():
        d['forced'] = True
        r.stop()
    r.callLater(timeout_secs, force_stop)
    yield r
    if d['forced']: pytest.fail(
        'Test did not stop reactor within {} secs'.format(timeout_secs))

def test_reactor_fixture(reactor):
    #   Comment out the next line to see "test did not stop reactor."
    reactor.callWhenRunning(reactor.stop)
    reactor.run()

####################################################################
#   Functional Tests

#   Global configuration for all functional tests.
os.environ.pop('SSH_AUTH_SOCK', None)
DEVNULL = open(os.devnull, 'rwb')

def test_global_config():
    assert None is os.environ.get('SSH_AUTH_SOCK')

def test_popen_ssh():
    'Demonstrate use of Popen in a test.'
    p = Popen(['ssh', '-n', '-h'], stdin=DEVNULL, stdout=PIPE, stderr=PIPE,
        env={}, bufsize=-1, close_fds=True)
    assert 0 <= p.wait()            # Any retval but not terminated by a signal.
    assert '' == p.stdout.read()    # XXX should close these?
    assert re.search('usage: ssh', p.stderr.read())

class SSHClientProto(protocol.ProcessProtocol):
    def __init__(self, reactor, received):
        self.reactor, self.received = reactor, received
    def connectionMade(self):
        self.transport.closeStdin()     # Send no input
    def errReceived(self, data):
        self.received.append(data)
    def processEnded(self, reason):
        self.reactor.stop()

def test_twisted_ssh(reactor):
    '   Demonstrate launch of OpenSSH client via twisted   '
    received = []
    proto = SSHClientProto(reactor, received)
    reactor.spawnProcess(proto, 'ssh', ['ssh', '-h'])   # Empty environment
    reactor.run()
    assert re.search('usage: ssh', ''.join(received))
