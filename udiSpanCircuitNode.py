#!/usr/bin/env python3

import time

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=30)



class udiSpanCircuitNode(udi_interface.Node):
    from  udiLib import openClose2ISY, priority2ISY, mask2key, bool2ISY, round2ISY, my_setDriver

    def __init__(self, polyglot, primary, address, name, span_access, circuit):
        logging.info(f'_init_ Span Circuit Node {name}')
        self.poly = polyglot
        self.span_panel = span_access
        self.circuit = circuit
        
        self.node_ok = False
        self.address = address
        self.primary = primary
        self.name = name
        self.node = self
        self.poly.subscribe(self.poly.START, self.start, address)

    def start(self):   
        logging.debug(f'Start Span Circuit node {self.name}')
        if self.node_ok:
            logging.debug(f'Span Circuit node {self.name} already initialized')
            return
        self.node = self.poly.getNode(self.address) or self
        self.update_data()
        self.updateISYdrivers()
        self.node_ok = True

    def stop(self):
        logging.debug('stop - Cleaning up')
    
    def node_ready(self):
        return(self.node_ok)

    def update_data(self, force=False):
        if not force and self.span_panel and self.circuit in (self.span_panel.span_data.get('circuit_info') or {}):
            return
        code = self.span_panel.update_panel_breaker_info(self.circuit)

    def updateISYdrivers(self):
        logging.debug(f'SpanCircuit updateISYdrivers {self.name}')
        #logging.debug(f'data: {self.span_panel.span_data}')
        pwr, pwr_time = self.span_panel.get_breaker_instant_power(self.circuit)
        pwr_val = round(-pwr, 1) if isinstance(pwr, (int, float)) else None
        self.my_setDriver('ST', pwr_val, 73)
        self.my_setDriver('GV1', self.priority2ISY(self.span_panel.get_breaker_priority(self.circuit)), 25)
        self.my_setDriver('GV2', self.openClose2ISY(self.span_panel.get_breaker_state(self.circuit)), 25)
        if pwr_time is not None:
            self.my_setDriver('GV4', pwr_time, 151)
        imp_wh, exp_wh, energy_time = self.span_panel.get_breaker_energy_info(self.circuit)
        if type(imp_wh) in (int, float):
            self.my_setDriver('GV5', round(imp_wh / 1000.0, 3), 33)
        else:
            self.my_setDriver('GV5', None, 25)
        if type(exp_wh) in (int, float):
            self.my_setDriver('GV6', round(exp_wh / 1000.0, 3), 33)
        else:
            self.my_setDriver('GV6', None, 25)
        producedWh, consumerWh = self.span_panel.get1HourAverage(self.circuit)
        
        if type(producedWh) in (int, float) and type(consumerWh) in (int, float):            
            self.my_setDriver('GV7', -round((producedWh- consumerWh),1), 119)
        else:
            self.my_setDriver('GV7', None, 25)
        producedWh, consumerWh = self.span_panel.get24HourAverage(self.circuit)   
        if type(producedWh) in (int, float) and type(consumerWh) in (int, float):                                  
            self.my_setDriver('GV8', -round((producedWh- consumerWh),1), 119) 
        else:
            self.my_setDriver('GV8', None, 25)           
        if energy_time is not None:
            self.my_setDriver('GV9', energy_time, 151)  

    def ISYupdate (self, command):
        logging.debug('ISY-update called')
        #self.update_PW_data(self.site_id, 'all')
        self.update_data(force=True)
        self.updateISYdrivers()

    def set_breaker(self, command):
        logging.debug(f'set_breaker called: {command}')
        if 'query' in command:
            state = int(command['query']['openclose.uom25'])
            if (0 == state):
                res =  self.span_panel.set_breaker_state(self.circuit, 'CLOSED')

            else:
                res = self.span_panel.set_breaker_state(self.circuit, 'OPEN')
            if res:
                self.my_setDriver('GV2', state, 25)


    def set_priority(self, command):
        logging.debug(f'set_priority called: {command}')
        if 'query' in command:
            priority = int(command['query']['priority.uom25'])
            if (0 == priority):
                res =  self.span_panel.set_breaker_priority(self.circuit, 'MUST_HAVE')
            elif (1 == priority):
                res =  self.span_panel.set_breaker_priority(self.circuit, 'NICE_TO_HAVE')
            else:
                res = self.span_panel.set_breaker_priority(self.circuit, 'NOT_ESSENTIAL')
            if res:
                self.my_setDriver('GV1', priority)   



    id = 'spancircuit'
    commands = {    
                'UPDATE'    : ISYupdate, 
                'OPENCLOSE' : set_breaker,
                #'PRIORITY'  : set_priority  Not workling yet - generates internal error
                }
    '''
        <st id="ST" editor="OPENCLOSE" /> breaker
        <st id="GV1" editor="PRIORITY" /> priority
        <st id="GV2" editor="KW" /> inst Power

        <st id="GV4" editor="SECS" /> Time sinse result (sec)
        <st id="GV5" editor="KWH" /> Imported Energy
        <st id="GV6" editor="KWH" />  Exported energy
        <st id="GV7" editor="KWH" /> energy / hour
        <st id="GV8" editor="KWH" />  energy / day       
        <st id="GV9" editor="SECS" />  Time since result (sec)
    '''

    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 73},         
            {'driver': 'GV1', 'value': 0, 'uom': 25},
            {'driver': 'GV2', 'value': 99, 'uom': 25},  
            {'driver': 'GV4', 'value': 0, 'uom': 151},  

            {'driver': 'GV5', 'value': 0, 'uom': 33},  
            {'driver': 'GV6', 'value': 0, 'uom': 33},  
            {'driver': 'GV7', 'value': 99, 'uom': 119},  
            {'driver': 'GV8', 'value': 99, 'uom': 119}, 

            {'driver': 'GV9', 'value': 0, 'uom': 151},           

            ]

    
