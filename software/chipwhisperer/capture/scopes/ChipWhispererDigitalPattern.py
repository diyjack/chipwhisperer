#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2014, NewAE Technology Inc
# All rights reserved.
#
# Authors: Colin O'Flynn
#
# Find this and more at newae.com - this file is part of the chipwhisperer
# project, http://www.assembla.com/spaces/chipwhisperer
#
#    This file is part of chipwhisperer.
#
#    chipwhisperer is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    chipwhisperer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with chipwhisperer.  If not, see <http://www.gnu.org/licenses/>.
#=================================================

import sys
from functools import partial
import numpy as np

from PySide.QtCore import *
from PySide.QtGui import *

try:
    from pyqtgraph.parametertree import Parameter
except ImportError:
    print "ERROR: PyQtGraph is required for this program"
    sys.exit()

from openadc.ExtendedParameter import ExtendedParameter
import chipwhisperer.common.ParameterTypesCustom
from chipwhisperer.capture.utils.SerialProtocols import strToBits as strToBits
from chipwhisperer.capture.utils.SerialProtocols import CWCalcClkDiv as CalcClkDiv

CODE_READ       = 0x80
CODE_WRITE      = 0xC0

ADDR_TRIGCLKDIV = 36
ADDR_TRIGIOPROG = 37


class CWAdvTrigger(object):
    def __init__(self):
        super(CWAdvTrigger, self).__init__()
        self.oa = None

    def con(self, oa):
        self.oa = oa

    def setExtPin(self, line):
        return

    def setIOPattern(self, pattern, form='units', clkdiv=None, hackit=3):
        ''' Setup the IO trigger pattern.'''
        "Form can be 'units' or 'seconds'. If set to 'units' you"
        "must also set the clkdiv parameter properly"

        # Pattern format:
        # [state, low, high]
        # state = 1/0
        # low = time in seconds/units
        # high = time in seconds/units
        # Special high variables:
        # Set to 'now' means next state after low time passes
        # high = 'now'
        # Set to 'wait' means no upper limit, but wait for transition
        # of IO line before changing state
        # high = 'wait'

        if len(pattern) > 63:
            raise ValueError("pattern too long: Hardware supports max of 64 pattern points")

        addr = 0
        for p in pattern:
            state = p[0]
            low = p[1]
            high = p[2]
            # TODO: support seconds
            if form == 'seconds':
                print "Not Supported"

            if high == 'now':
                high = 511

            if high == 'wait':
                high = 510

            # Addr = 0 has several samples taken at 'full speed' before clock divider
            # gets pushed in. The following seems to typically work to compensate, but
            # at high speeds this might be wrong.
            # TODO: This might require us to know oversample rate for properly doing this
            if addr == 0:
                low += hackit
                high += hackit

                if (low >= 510) or (high >= 510):
                    raise ValueError("low or high for addr=0 too large!")

            # print "%04d: %2d - %2d" % (addr, low, high)

            self.writeOnePattern(addr, state, low, high)
            addr = addr + 1

        # Set done marker
        self.writeOnePattern(addr, 1, 255, 511)

        if clkdiv:
            self.writeClockDiv(clkdiv)

    def writeClockDiv(self, clkdiv):
        clkdiv = int(clkdiv)
        d = bytearray()
        d.append(clkdiv & 0xff)
        d.append((clkdiv >> 8) & 0xff)
        d.append((clkdiv >> 16) & 0xff)
        self.oa.sendMessage(CODE_WRITE, ADDR_TRIGCLKDIV, d)

    def reset(self):
        resp = self.oa.sendMessage(CODE_READ, ADDR_TRIGCLKDIV, Validate=False, maxResp=3)
        # Assert Reset
        resp[2] = resp[2] | 0x80
        self.oa.sendMessage(CODE_WRITE, ADDR_TRIGCLKDIV, resp)

        # Deassert Reset
        resp[2] = resp[2] & 0x7F;
        self.oa.sendMessage(CODE_WRITE, ADDR_TRIGCLKDIV, resp)

    def writeOnePattern(self, addr, state, low, high):
        d = bytearray()
        d.append(low)
        d.append(high & 0xff)
        d.append((0x01 & (high >> 8)) | (state << 1))
        d.append(addr)
        self.oa.sendMessage(CODE_WRITE, ADDR_TRIGIOPROG, d)

    def processBit(self, state, cnt, first=False, last=False, var=1, osRate=3):
        cnt = osRate * cnt
        low = cnt - var
        high = cnt + var

        if low < 1:
            low = 1

        if high > 509:
            high = 509

        if first:
            high = 'wait'

        if last:
            high = 'now'

        return [state, low, high]

    def bitsToPattern(self, bits, osRate=3, threshold=1):
        pattern = []
        lastbit = 2
        bitcnt = 0
        first = True
        for b in bits:
            if b == lastbit:
                bitcnt = bitcnt + 1
            else:
                if bitcnt > 0:
                    # print "%d %d"%(lastbit, bitcnt)
                    pattern.append(self.processBit(lastbit, bitcnt, first=first, var=threshold, osRate=osRate))
                lastbit = b
                bitcnt = 1

            first = False
        pattern.append(self.processBit(lastbit, bitcnt, last=True))
        return pattern

    def strToPattern(self, string, startbits=1, stopbits=1, parity='none'):
        return self.bitsToPattern(totalpat)

class ChipWhispererDigitalPattern(QObject):
    """
    Communicates and drives with the Digital Pattern Match module inside the FPGA. 
    """

    paramListUpdated = Signal(list)

    def __init__(self, showScriptParameter=None, CWMainWindow=None):

        self.cwAdv = CWAdvTrigger()   
        

        paramSS = [
                 {'name':'Serial Settings', 'type':'group', 'children':[
                      {'name':'Baud', 'key':'baud', 'type':'int', 'limits':(100, 500000), 'value':38400, 'step':100, 'set':self.updateSampleRate},
                      {'name':'Start Bits', 'key':'startbits', 'type':'int', 'limits':(1, 10), 'value':1},
                      {'name':'Stop Bits', 'key':'stopbits', 'type':'int', 'limits':(1, 10), 'value':1},
                      {'name':'Parity', 'key':'parity', 'type':'list', 'values':['none', 'even'], 'value':'none'},
                    ]},

                 # TODO: Need to confirm oversample rate stuff
                 {'name':'Oversample Rate', 'key':'osrate', 'type':'int', 'limits':(2, 5), 'value':3, 'set':self.updateSampleRate},
                 {'name':'Calculated Clkdiv', 'key':'calcclkdiv', 'type':'int', 'readonly':True},
                 {'name':'Calculated Error', 'key':'calcerror', 'type':'int', 'suffix':'%', 'readonly':True},
                 {'name':'Trigger Character', 'key':'trigpatt', 'type':'str', 'value':'""', 'set':self.setPattern},
                 {'name':'Binary Pattern', 'key':'binarypatt', 'type':'str', 'value':''},
                 {'name':'Reset Module', 'type':'action', 'action':self.reset},
                 
                {'name':'Advanced Settings', 'type':'group', 'children':[
                 {'name':'Threshold', 'key':'threshold', 'type':'int', 'value':1, 'limits':(1, 10), 'set':self.reset},
                 {'name':'Initial Bit Correction', 'key':'initialcorrect', 'type':'int', 'value':3, 'limits':(0, 10), 'set':self.reset},
                 ]}
                ]
            
        self.oa = None
        self.params = Parameter.create(name='Digital Pattern Trigger Module', type='group', children=paramSS)
        ExtendedParameter.setupExtended(self.params, self)
        self.showScriptParameter = showScriptParameter
        
    def paramTreeChanged(self, param, changes):
        if self.showScriptParameter is not None:
            self.showScriptParameter(param, changes, self.params)

    def reset(self, ignored=None):
        # Reload pattern
        self.setPattern(self.findParam('trigpatt').value())

    def updateSampleRate(self, ignored=None):
        res = CalcClkDiv(self.oa.hwInfo.sysFrequency(), self.findParam('baud').value() * self.findParam('osrate').value())
        self.findParam('calcclkdiv').setValue(res[0])
        self.findParam('calcerror').setValue(res[1] * 100)
        self.clkdiv = res[0]
        self.reset()

    def setPattern(self, patt):
        patt = eval(patt, {}, {})

        if len(patt) > 1:
            print "WARNING: IO Pattern too large! Restricted."
            self.findParam('trigpatt').setValue(patt[0])
            return

        # Convert to bits
        bitpattern = strToBits(patt, startbits=self.findParam('startbits').value(),
                               stopbits=self.findParam('stopbits').value(),
                               parity=self.findParam('parity').value())

        # Convert to pattern & Download
        try:
            pat = self.cwAdv.bitsToPattern(bitpattern, osRate=self.findParam('osrate').value(),
                                                       threshold=self.findParam('threshold').value())
            self.cwAdv.setIOPattern(pat, clkdiv=self.clkdiv, hackit=self.findParam('initialcorrect').value())

            bitstr = ""
            for t in bitpattern: bitstr += "%d" % t

        except ValueError, s:
            bitstr = "Error: %s" % s

        self.findParam('binarypatt').setValue(bitstr)


    def setOpenADC(self, oa):
        """ Pass a reference to OpenADC, used for communication with ChipWhisperer """

        self.oa = oa.sc

        self.cwAdv.con(oa.sc)
        self.params.getAllParameters()
        self.updateSampleRate()

    def paramList(self):
        p = []
        p.append(self.params)            
        return p
    
