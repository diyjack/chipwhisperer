#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2014, NewAE Technology Inc
# All rights reserved.
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

import numpy as np
import os

class tracereader_native:
    def __init__(self):
        self.NumTrace = None
        self.NumPoint = None
        self.textints = None
        self.textouts = None
        self.knownkey = None
        self.directory = None
        self.tracesSaved = False
        self.tracedtype = None

    def copyTo(self, srcTraces=None):
        self.NumTrace = srcTraces.NumTrace
        self.NumPoint = srcTraces.NumPoint
        self.knownkey = srcTraces.knownkey

        self.textins = np.zeros([self.NumTrace, 16], dtype=np.uint8)
        for n in range(0, self.NumTrace):
            tin = srcTraces.textins[n]
            self.textins[n] = map(int, tin, [16]*len(tin))
        

        self.textouts = np.zeros([self.NumTrace, 16], dtype=np.uint8)
        for n in range(0, self.NumTrace):
            tout = srcTraces.textouts[n]
            self.textouts[n] = map(int, tout, [16]*len(tout))

        if srcTraces.tracedtype:
            userdtype = srcTraces.tracedtype
        else:
            userdtype = np.float
            
        self.traces = np.array(srcTraces.traces, dtype=userdtype)

        #Traces copied in means not saved
        self.tracesSaved = False
        
        
    def loadAllTraces(self, directory=None, prefix=""):
        self.traces = np.load(directory + "/%straces.npy"%prefix)
        self.textins = np.load(directory + "/%stextin.npy"%prefix)
        self.textouts = np.load(directory + "/%stextout.npy"%prefix)
        self.knownkey = np.load(directory + "/%sknownkey.npy"%prefix)

        self.NumTrace = self.traces.shape[0]
        self.NumPoint = self.traces.shape[1]

        #Traces loaded means saved
        self.tracesSaved = True
        return

    def saveAllTraces(self, directory, prefix=""):
        np.save(directory + "/%straces.npy"%prefix, self.traces)
        np.save(directory + "/%stextin.npy"%prefix, self.textins)
        np.save(directory + "/%stextout.npy"%prefix, self.textouts)
        np.save(directory + "/%sknownkey.npy"%prefix, self.knownkey)
        self.tracesSaved = True

    def numPoints(self):
        return self.NumPoint

    def numTraces(self):
        return self.NumTrace

    def getTrace(self, n):
        data = self.traces[n]

        #Following line will normalize all traces relative to each
        #other by mean & standard deviation
        #data = (data - np.mean(data)) / np.std(data)
        
        return data

    def getTextin(self, n):
        return self.textins[n]

    def getTextout(self, n):
        return self.textouts[n]

    def getKnownKey(self):
        return self.knownkey
    
    
    
