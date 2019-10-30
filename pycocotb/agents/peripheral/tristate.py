from collections import deque
from typing import Tuple, Union

from pycocotb.agents.base import AgentWitReset, NOP
from pycocotb.agents.clk import DEFAULT_CLOCK
from pycocotb.hdlSimulator import HdlSimulator
from pycocotb.triggers import Timer, WaitWriteOnly, WaitCombRead, Edge


class TristateAgent(AgentWitReset):
    """
    :ivar selfSynchronization: if True the agent reads/write
        with a perior of DEFAULT_CLOCK
    :ivar pullMode: specifies how the interface should behave if none drives it
        can be (1: pull-up, 0: pull-down, None: disconnected)
    """

    def __init__(self,
                 sim: HdlSimulator,
                 intf: Tuple["RtlSignal", "RtlSignal", "RtlSignal"],
                 rst: Tuple["RtlSignal", bool]):
        """
        :param intf: tuple (i signal, o signal, t signal)
            as present in tristate interface
        :note: t signal controls if the output should be connected,
            if 't'=0 the 'o' does not have effect
        """
        super(TristateAgent, self).__init__(sim, intf, rst)
        self.i, self.o, self.t = intf
        self.data = deque()
        # can be (1: pull-up, 0: pull-down, None: disconnected)
        self.pullMode: Union[1, 0, None] = 1
        self.selfSynchronization = True
        self.collectData = True

    def monitor(self):
        """
        The evaluate a tristate 'i' value from 'o' and 't'
        and optionaly store it.
        One step.
        """
        yield WaitCombRead()
        # read in pre-clock-edge
        t = self.t.read()
        o = self.o.read()
        sim = self.sim
        if self.pullMode is not None and sim.now > 0:
            try:
                t = int(t)
            except ValueError:
                raise AssertionError(
                    sim.now, self.t, "This mode, this value => ioblock would burn")
            try:
                o = int(o)
            except ValueError:
                raise AssertionError(
                    sim.now, self.o, "This mode, this value => ioblock would burn")

            if self.pullMode != o:
                raise AssertionError(
                    sim.now, self.o, "This mode, this value => ioblock would burn")

        if t:
            v = o
        else:
            v = self.pullMode

        last = self.i.read()
        try:
            last = int(last)
        except ValueError:
            last = None

        yield WaitWriteOnly()
        self.i.write(v)

        if self.collectData and sim.now > 0:
            yield WaitCombRead()
            if self.notReset():
                self.data.append(v)

    def getMonitors(self):
        return [self.onTWriteCallback(), ]

    def onTWriteCallback(self, sim):
        while True:
            yield Edge(self.t, self.o)

            if self.getEnable():
                yield from self.monitor(sim)

    def _write(self, val: Union[int, NOP]):
        """
        Update value on interface.
        """
        if val is NOP:
            # control now has slave
            t = 0
            o = self.pullMode
        else:
            # control now has this agent
            t = 1
            o = val

        self.t.write(t)
        self.o.write(o)

    def _read(self):
        """
        :return: actual value on interface
        """
        return self.i.read()

    def driver(self):
        """
        Drive 'o' and 't' from data buffer.
        One step if not selfSynchronization else infinite loop.
        """
        while True:
            yield WaitWriteOnly()
            if self.data:
                o = self.data.popleft()
                if o == NOP:
                    t = 0
                    o = 0
                else:
                    t = 1
                self.o.write(o)
                self.t.write(t)

            if self.selfSynchronization:
                yield Timer(DEFAULT_CLOCK)
            else:
                break


class TristateClkAgent(TristateAgent):
    """
    Agent for tri-state interface which generates clock signal
    """

    def __init__(self, sim: HdlSimulator, intf, rst: Tuple["RtlSignal", bool]):
        super(TristateClkAgent, self).__init__(sim, intf, rst)
        self.period = DEFAULT_CLOCK
        self.collectData = False

    def driver(self):
        o = self.o
        high = self.pullMode
        low = not self.pullMode
        halfPeriod = self.period // 2

        yield WaitWriteOnly()
        o.write(low)
        self.t.write(1)

        while True:
            yield Timer(halfPeriod)
            yield WaitWriteOnly()
            o.write(high)

            yield Timer(halfPeriod)
            yield WaitWriteOnly()
            o.write(low)