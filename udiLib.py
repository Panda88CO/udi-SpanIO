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
import os
import json
import time
import threading
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
    if s in ['MUST_HAVE', 'NEVER']:
        return 0
    elif s in ['NICE_TO_HAVE', 'SOC_THRESHOLD']:
        return 1
    elif s in ['NOT_ESSENTIAL', 'NON_ESSENTIAL', 'OFF_GRID']:
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

def my_setDriver(self, key, value, Unit=None, force=False):
    target = getattr(self, 'node', None) or self
    force_val = bool(force)
    logging.debug('my_setDriver : {} {} {} force={}'.format(key, value, Unit, force_val))
    if value is None:
        logging.debug('None value passed = seting 99, UOM 25')
        target.setDriver(key, 99, True, force_val, uom=25)
    else:
        if Unit:
            target.setDriver(key, value, True, force_val, uom=Unit)
        else:
            target.setDriver(key, value, True, force_val)



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
    logging.debug('heartbeat: pulse DON -> wait 5s -> DOF')
    def _pulse():
        try:
            self.reportCmd('DON', 2)
            time.sleep(5)
            self.reportCmd('DOF', 2)
        except Exception as e:
            logging.error(f'Error pulsing heartbeat: {e}')

    threading.Thread(target=_pulse, name='HeartbeatPulse', daemon=True).start()

def handleLevelChange(self, level):
    logging.info('New log level: {}'.format(level))        


class SpanNodeNameManager:
    """
    Manages node name persistence and synchronization between the SPAN API
    and Polyglot PG3x / IoX.

    Rules:
    1. If the node name was changed in PG3x / IoX, we remember and use the stored/mapped name.
    2. If a new name arrives from the SPAN API (different from the stored original name),
       the new API name takes precedence: we overwrite the stored mapped name and update
       PG3x / IoX (rename=True).
    3. If the API name matches the stored original name, but the stored/PG3x name is different,
       we use the stored name (preserving user customization).
    """

    FILE_PATH = 'node_names.json'

    def __init__(self, poly=None, custom_data=None):
        self.poly = poly
        self.custom_data = custom_data
        self.name_map = {}  # {address: {'original': str, 'mapped': str}}
        self.load()

    def set_custom_data(self, custom_data):
        self.custom_data = custom_data
        self.load()

    def load(self):
        # 1. Load from local file if exists
        try:
            if os.path.exists(self.FILE_PATH):
                with open(self.FILE_PATH, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for addr, entry in data.items():
                            if isinstance(entry, dict):
                                self.name_map[addr] = {
                                    'original': str(entry.get('original', '')),
                                    'mapped': str(entry.get('mapped', ''))
                                }
        except Exception as e:
            logging.warning(f'SpanNodeNameManager: could not read {self.FILE_PATH}: {e}')

        # 2. Merge with custom_data if available
        if self.custom_data is not None:
            try:
                cd_map = self.custom_data.get('node_name_map')
                if isinstance(cd_map, dict):
                    for addr, entry in cd_map.items():
                        if isinstance(entry, dict):
                            self.name_map[addr] = {
                                'original': str(entry.get('original', '')),
                                'mapped': str(entry.get('mapped', ''))
                            }
            except Exception as e:
                logging.warning(f'SpanNodeNameManager: could not read custom_data: {e}')

    def save(self):
        # 1. Save to custom_data (persisted in PG3 database)
        if self.custom_data is not None:
            try:
                self.custom_data['node_name_map'] = dict(self.name_map)
            except Exception as e:
                logging.warning(f'SpanNodeNameManager: could not save to custom_data: {e}')

        # 2. Save to local file
        try:
            with open(self.FILE_PATH, 'w') as f:
                json.dump(self.name_map, f, indent=2)
        except Exception as e:
            logging.warning(f'SpanNodeNameManager: could not write {self.FILE_PATH}: {e}')

    def get_db_name(self, address, poly=None, nodes_in_db=None):
        """Finds current name for address in PG3 DB."""
        p = poly or self.poly
        if p and hasattr(p, 'getNodeNameFromDb') and callable(getattr(p, 'getNodeNameFromDb')):
            try:
                name = p.getNodeNameFromDb(address)
                if name:
                    return str(name).strip()
            except Exception:
                pass

        if nodes_in_db:
            if isinstance(nodes_in_db, list):
                for n in nodes_in_db:
                    if isinstance(n, dict) and n.get('address') == address:
                        name = n.get('name')
                        if name:
                            return str(name).strip()
            elif isinstance(nodes_in_db, dict):
                n = nodes_in_db.get(address)
                if isinstance(n, dict):
                    name = n.get('name')
                    if name:
                        return str(name).strip()

        if p and hasattr(p, 'getNodesFromDb') and callable(getattr(p, 'getNodesFromDb')):
            try:
                db_nodes = p.getNodesFromDb()
                if isinstance(db_nodes, list):
                    for n in db_nodes:
                        if isinstance(n, dict) and n.get('address') == address:
                            name = n.get('name')
                            if name:
                                return str(name).strip()
                elif isinstance(db_nodes, dict):
                    n = db_nodes.get(address)
                    if isinstance(n, dict):
                        name = n.get('name')
                        if name:
                            return str(name).strip()
            except Exception:
                pass

        return None

    def resolve_node_name(self, address, api_name, poly=None, nodes_in_db=None):
        """
        Resolves the appropriate name for a node according to the rules:
        - If original name is new (api_name != stored original), overwrite PG3x (rename=True).
        - If original name matches stored original, but stored mapped name (or PG3x DB name)
          is different, use the stored mapped name (rename=False).
        - Returns (resolved_name, rename_needed).
        """
        p = poly or self.poly
        clean_api_name = p.getValidName(api_name) if p and hasattr(p, 'getValidName') else str(api_name).strip()
        db_name = self.get_db_name(address, p, nodes_in_db)

        entry = self.name_map.get(address)
        if not entry or not isinstance(entry, dict):
            # First time seeing this node
            if db_name and db_name != clean_api_name:
                # Existing node in PG3 DB already has a custom name from user
                stored_orig = clean_api_name
                stored_mapped = db_name
                resolved_name = db_name
                rename_needed = False
                logging.info(f'SpanNodeNameManager [{address}]: Initialized existing DB mapped name "{resolved_name}" (API original was "{stored_orig}")')
            else:
                stored_orig = clean_api_name
                stored_mapped = clean_api_name
                resolved_name = clean_api_name
                rename_needed = False
                logging.info(f'SpanNodeNameManager [{address}]: Initialized new node with API name "{resolved_name}"')

            self.name_map[address] = {'original': stored_orig, 'mapped': stored_mapped}
            self.save()
            return resolved_name, rename_needed

        stored_orig = entry.get('original')
        stored_mapped = entry.get('mapped')

        # Rule 1: Is original name from API new?
        if stored_orig is not None and clean_api_name != stored_orig:
            logging.info(f'SpanNodeNameManager [{address}]: New name from API! "{stored_orig}" -> "{clean_api_name}". Overwriting mapped name "{stored_mapped}".')
            self.name_map[address] = {'original': clean_api_name, 'mapped': clean_api_name}
            self.save()
            return clean_api_name, True

        # Rule 2: Original name unchanged. Check if user changed name in PG3x / IoX
        if db_name and db_name != stored_mapped:
            logging.info(f'SpanNodeNameManager [{address}]: Detected name change in PG3x: "{stored_mapped}" -> "{db_name}". Updating mapped name.')
            stored_mapped = db_name
            self.name_map[address] = {'original': stored_orig, 'mapped': stored_mapped}
            self.save()

        # If stored name is different from original, use stored name
        if stored_mapped and stored_mapped != stored_orig:
            logging.debug(f'SpanNodeNameManager [{address}]: Using stored mapped name "{stored_mapped}" (API name is "{stored_orig}")')
            return stored_mapped, False

        return clean_api_name, False
