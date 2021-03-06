from fjagepy import *
from fjagepy import Message as _Message
from fjagepy import MessageClass as _MessageClass
from fjagepy import Performative as _Performative
from fjagepy import Gateway as _Gateway
from fjagepy import AgentID as _AgentID
from types import MethodType as _mt
from warnings import warn as _warn

_ParameterReq = _MessageClass('org.arl.unet.ParameterReq')
_ParameterRsp = _MessageClass('org.arl.unet.ParameterRsp')


def _short(p):
    return p.split('.')[-1]


def _value(v):
    # TODO: support complex objects
    if isinstance(v, dict):
        if 'clazz' in v:
            if v['clazz'] == 'java.util.Date':
                return v['data']
            if v['clazz'] == 'java.util.ArrayList':
                return v['data']
            return v['clazz'] + '(...)'
        if 'data' in v:
            return v['data']
    return v


class Services:
    NODE_INFO = 'org.arl.unet.Services.NODE_INFO'
    ADDRESS_RESOLUTION = 'org.arl.unet.Services.ADDRESS_RESOLUTION'
    DATAGRAM = 'org.arl.unet.Services.DATAGRAM'
    PHYSICAL = 'org.arl.unet.Services.PHYSICAL'
    RANGING = 'org.arl.unet.Services.RANGING'
    BASEBAND = 'org.arl.unet.Services.BASEBAND'
    LINK = 'org.arl.unet.Services.LINK'
    MAC = 'org.arl.unet.Services.MAC'
    ROUTING = 'org.arl.unet.Services.ROUTING'
    ROUTE_MAINTENANCE = 'org.arl.unet.Services.ROUTE_MAINTENANCE'
    TRANSPORT = 'org.arl.unet.Services.TRANSPORT'
    REMOTE = 'org.arl.unet.Services.REMOTE'
    STATE_MANAGER = 'org.arl.unet.Services.STATE_MANAGER'


class ParameterReq(_ParameterReq):

    def __init__(self, index=-1, **kwargs):
        super().__init__()
        self.index = index
        self.requests = []
        self.perf = _Performative.REQUEST
        self.__dict__.update(kwargs)

    def get(self, param):
        self.requests.append({'param': param});
        return self

    def set(self, param, value):
        self.requests.append({'param': param, 'value': value});
        return self


class ParameterRsp(_ParameterRsp):

    def __init__(self, **kwargs):
        super().__init__()
        self.index = -1
        self.values = dict()
        self.perf = _Performative.REQUEST
        self.__dict__.update(kwargs)


def get(msg, param):
    if 'param' in msg.__dict__ and msg.param == param:
        return _value(self.value)
    if 'values' in msg.__dict__ and param in msg.values:
        return _value(msg.values[param])
    if 'param' in msg.__dict__ and _short(msg.param) == param:
        return _value(msg.value)
    if 'values' not in msg.__dict__:
        return None
    for v in self.values:
        if _short(v) == param:
            return _value(msg.values[v])
    return None


def parameters(msg):
    if 'values' in msg.__dict__:
        p = msg.values.copy()
    else:
        p = {}
    if 'param' in msg.__dict__:
        p[msg.param] = msg.value
    for k in p:
        if isinstance(p[k], dict):
            p[k] = _value(p[k])
    return p


def _repr_pretty_(self, p, cycle):
    if cycle:
        p.text('...')
    elif self.perf is not None:
        p.text(self.perf)


setattr(_Message, '_repr_pretty_', _repr_pretty_)


class AgentID(_AgentID):

    def __init__(self, gw, name, is_topic=False):
        self.is_topic = is_topic
        self.name = name
        self.index = -1
        self.gw = gw

    def send(self, msg):
        msg.recipient = self.name
        return self.gw.send(msg)

    def request(self, msg, timeout=1000):
        msg.recipient = self.name
        return self.gw.request(msg, timeout)

    def __lshift__(self, msg):
        return self.request(msg)

    def __getattr__(self, param):
        rsp = self.request(ParameterReq(index=self.index).get(param))
        if rsp is None:
            return None
        return get(rsp, param)

    def __setattr__(self, param, value):
        if param in ['name', 'gw', 'is_topic', 'index']:
            self.__dict__[param] = value
            return value
        rsp = self.request(ParameterReq(index=self.index).set(param, value))
        if rsp is None:
            _warn('Could not set parameter ' + param)
            return None
        v = get(rsp, param)
        if v != value:
            _warn('Parameter ' + param + ' set to ' + str(v))
        return v

    def __getitem__(self, index):
        c = AgentID(self.gw, self.name)
        c.index = index
        return c

    def __str__(self):
        peer = self.gw.socket.getpeername()
        return self.name + ' on ' + peer[0] + ':' + str(peer[1])

    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text('...')
            return
        rsp = self.request(ParameterReq(index=self.index))
        if rsp is None:
            p.text(self.__str__())
            return
        params = parameters(rsp)
        oprefix = ''
        for param in sorted(params):
            pp = param.split('.')
            prefix = '.'.join(pp[:-1]) if len(pp) > 1 else ''
            if prefix != oprefix:
                oprefix = prefix
                p.text('\n[' + prefix + ']\n')
            p.text('  ' + pp[-1] + ' = ' + str(params[param]) + '\n')


class UnetGateway(_Gateway):

    def __init__(self, hostname, port=1100, name=None):
        super().__init__(hostname, port, name)

    def topic(self, name):
        a = super().topic(name)
        return AgentID(self, a.name, a.is_topic)

    def agent(self, name):
        return AgentID(self, name)

    def agentForService(self, service):
        a = super().agentForService(service)
        if a is not None:
            if isinstance(a, str):
                a = AgentID(self, a)
            else:
                a = AgentID(self, a.name, a.is_topic)
        return a

    def agentsForService(self, service):
        a = super().agentsForService(service)
        if a is not None:
            for j in range(len(a)):
                if isinstance(a[j], str):
                    a[j] = AgentID(self, a[j])
                else:
                    a[j] = AgentID(self, a[j].name)
        return a

    def agent(self, name):
        return AgentID(self, name)
