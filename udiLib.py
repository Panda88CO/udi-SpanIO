#!/usr/bin/env python3
"""
Polyglot TEST v3 node server 


MIT License
"""

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)

from os import truncate
import time
import math
import numbers 
import random, string

def random_string(self, length):
    x = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))
    return(x)

def node_queue(self, data):
    #logging.debug('node_queue {}'.format(data))
    if isinstance(data, dict):
        if 'address' in data:
            self.n_queue.append(data['address'])
    elif isinstance(data, str):
        self.n_queue.append(data)

def wait_for_node_done(self, address=None):
    target_address = address if address is not None else getattr(self, 'address', None)
    logging.debug(f'Waiting for node done: {target_address}')
    start_time = time.time()
    timeout = 20
    while time.time() - start_time < timeout:
        if target_address:
            if target_address in self.n_queue:
                self.n_queue.remove(target_address)
                logging.debug(f'Node done confirmed for: {target_address}')
                return True
        else:
            if len(self.n_queue) > 0:
                popped = self.n_queue.pop(0)
                logging.debug(f'Node done confirmed (popped {popped})')
                return True
        time.sleep(0.1)
    logging.warning(f'Timeout waiting for ADDNODEDONE for {target_address}')
    return False

def mask2key (self, mask):
    #logging.debug('mask2key : {}'.format(mask))
    return(int(round(math.log2(mask),0)))
    
def daysToMask (self, dayList):
    daysValue = 0 
    i = 0
    for day in self.daysOfWeek:
        if day in dayList:
            daysValue = daysValue + pow(2,i)
        i = i+1
    return(daysValue)

def maskToDays(self, daysValue):
    daysList = []
    for i in range(0,7):
        mask = pow(2,i)
        if (daysValue & mask) != 0 :
            daysList.append(self.daysOfWeek[i])
    return(daysList)

def openClose2ISY(self, state):
    logging.debug(f'openClose2ISY {state}')
    if state is None:
        return None
    if isinstance(state, (int, float)):
        return int(state) if state in [0, 1] else 99
    s = str(state).strip().upper()
    if s == 'OPEN':
        return 1
    elif s == 'CLOSED':
        return 0
    else:
        return 99

def priority2ISY(self, state):
    logging.debug(f'priority2ISY {state}')
    if state is None:
        return None
    if isinstance(state, (int, float)):
        return int(state) if state in [0, 1, 2] else 99
    s = str(state).strip().upper().replace(' ', '_')
    if s == 'MUST_HAVE':
        return 0
    elif s == 'NICE_TO_HAVE':
        return 1
    elif s in ['NOT_ESSENTIAL', 'NON_ESSENTIAL']:
        return 2
    else:
        return 99

def gridState2ISY(self, state):
    logging.debug(f'gridState2ISY {state}')
    if state is None:
        return None
    if isinstance(state, (int, float)):
        return int(state) if state in [0, 1] else 99
    s = str(state).strip().upper()
    if s in ['DSM_GRID_UP', 'GRID_UP', 'UP']:
        return 0
    elif s in ['DSM_GRID_DOWN', 'GRID_DOWN', 'DOWN']:
        return 1
    else:
        return 99

def gridStatus2ISY(self, status):
    logging.debug(f'gridStatus2ISY {status}')
    if status is None:
        return None
    if isinstance(status, (int, float)):
        return int(status) if status in [0, 1] else 99
    s = str(status).strip().upper()
    if s in ['ON_GRID', 'DSM_ON_GRID', 'GRID']:
        return 0
    elif s in ['OFF_GRID', 'DSM_ISLANDED', 'ISLANDED']:
        return 1
    else:
        return 99

def bool2Nbr(self, bool):
    if bool == True:
        return(1)
    elif bool == False:
        return(0)
    else:
        return(None)
    
def round2ISY(self, nbr, res):
    if isinstance(nbr, numbers.Number):
        return(round(nbr, res))
    else:
        return(None)

def bool2ISY (self, data):
    if data:
        return(1)
    else:
        return(0)

def state2Nbr(self, val):
    if val == 'normal':
        return(0)
    elif val == 'alert':
        return(1)
    else:
        return(99)

def isy_value(self, value):
    if value == None:
        return (99)
    else:
        return(value)
    
def daylist2bin(self, daylist):
    sum = 0
    if 'sun' in daylist:
        sum = sum + 1
    if 'mon' in daylist:
        sum = sum + 2       
    if 'tue' in daylist:
        sum = sum + 4
    if 'wed' in daylist:
        sum = sum + 8
    if 'thu' in daylist:
        sum = sum + 16
    if 'fri' in daylist:
        sum = sum + 32
    if 'sat' in daylist:
        sum = sum + 64
    return(sum)


def season2ISY(self, season):
    #logging.debug('season2ISY {}'.format(season))
    if season.upper() == 'WINTER':
        return(0)
    elif season.upper() == 'SUMMER':
        return(1)
    elif season != None:
        return(2)
    else:
        return (99)
    

def period2ISY(self, period):
    #logging.debug('period2ISY {}'.format(period))
    if period.upper() == 'OFF_PEAK':
        return(0)
    elif period.upper() == 'PARTIAL_PEAK':
        return(1)
    elif period.upper() == 'PEAK':
        return(2)
    else:
        return (99) 

def my_setDriver(self, key, value, Unit=None, force = None):
    target = getattr(self, 'node', None) or self
    logging.debug('my_setDriver : {} {} {}'.format(key, value, Unit))
    if value == None:
        logging.debug('None value passed = seting 99, UOM 25')
        target.setDriver(key, 99, True, force!=None, uom=25)
    else:
        if Unit:
            target.setDriver(key, value, True, force!=None, uom=Unit)
        else:
            target.setDriver(key, value, True, force!=None)



def send_rel_temp_to_isy(self, temperature, stateVar):
    logging.debug('convert_temp_to_isy - {}'.format(temperature))
    #logging.debug('ISYunit={}, Mess_unit={}'.format(self.ISY_temp_unit , self.messana_temp_unit ))
    if self.ISY_temp_unit == 0: # Celsius in ISY
        if self.messana_temp_unit == 'Celsius' or self.messana_temp_unit == 0:
            self.node.setDriver(stateVar, round(temperature,1), True, True, 4)
        else: # messana = Farenheit
            self.node.setDriver(stateVar, round(temperature*5/9,1), True, True, 17)
    elif  self.ISY_temp_unit == 1: # Farenheit in ISY
        if self.messana_temp_unit == 'Celsius' or self.messana_temp_unit == 0:
            self.node.setDriver(stateVar, round((temperature*9/5),1), True, True, 4)
        else:
            self.node.setDriver(stateVar, round(temperature,1), True, True, 17)
    else: # kelvin
        if self.messana_temp_unit == 'Celsius' or self.messana_temp_unit == 0:
            self.node.setDriver(stateVar, round((temperature,1), True, True, 4))
        else:
            self.node.setDriver(stateVar, round((temperature)*9/5,1), True, True, 17)


def send_temp_to_isy (self, temperature, stateVar):
    logging.debug('convert_temp_to_isy - {}'.format(temperature))
    #logging.debug('ISYunit={}, Mess_unit={}'.format(self.ISY_temp_unit , self.messana_temp_unit ))
    if self.ISY_temp_unit == 0: # Celsius in ISY
        if self.messana_temp_unit == 'Celsius' or self.messana_temp_unit == 0:
            self.node.setDriver(stateVar, round(temperature,1), True, True, 4)
        else: # messana = Farenheit
            self.node.setDriver(stateVar, round((temperature-32)*5/9,1), True, True, 17)
    elif  self.ISY_temp_unit == 1: # Farenheit in ISY
        if self.messana_temp_unit == 'Celsius' or self.messana_temp_unit == 0:
            self.node.setDriver(stateVar, round((temperature*9/5+32),1), True, True, 4)
        else:
            self.node.setDriver(stateVar, round(temperature,1), True, True, 17)
    else: # kelvin
        if self.messana_temp_unit == 'Celsius' or self.messana_temp_unit == 0:
            self.node.setDriver(stateVar, round((temperature+273.15,1), True, True, 4))
        else:
            self.node.setDriver(stateVar, round((temperature+273.15-32)*9/5,1), True, True, 17)



def heartbeat(self):
    logging.debug('heartbeat: ' + str(self.hb))
    
    if self.hb == 0:
        self.reportCmd('DON',2)
        self.hb = 1
    else:
        self.reportCmd('DOF',2)
        self.hb = 0

def handleLevelChange(self, level):
    logging.info('New log level: {}'.format(level))        