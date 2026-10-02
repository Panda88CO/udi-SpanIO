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
        self.updateISYdrivers(force=True)
        self.node_ok = True

    def stop(self):
        logging.debug('stop - Cleaning up')
    
    def node_ready(self):
        return(self.node_ok)

    def update_data(self, force=False):
        if not force and self.span_panel and self.circuit in (self.span_panel.span_data.get('circuit_info') or {}):
            return
        code = self.span_panel.update_panel_breaker_info(self.circuit)

    def updateISYdrivers(self, force=False):
        logging.debug(f'SpanCircuit updateISYdrivers {self.name} force={force}')
        pwr, pwr_time = self.span_panel.get_breaker_instant_power(self.circuit)
        pwr_val = round(-pwr, 1) if isinstance(pwr, (int, float)) else None
        if pwr_val == 0.0:
            pwr_val = 0.0

        force_report = force or (pwr is not None)

        self.my_setDriver('ST', pwr_val, 73, force=force_report)
        self.my_setDriver('GV1', self.priority2ISY(self.span_panel.get_breaker_priority(self.circuit)), 25, force=force_report)
        self.my_setDriver('GV2', self.openClose2ISY(self.span_panel.get_breaker_state(self.circuit)), 25, force=force_report)
        if pwr_time is not None:
            self.my_setDriver('GV4', pwr_time, 151, force=force_report)

        prod_wh, cons_wh, energy_time = self.span_panel.get_breaker_energy_info(self.circuit)
        force_energy = force or (energy_time is not None)

        # GV5: Imported (consumed) energy in kWh
        if isinstance(cons_wh, (int, float)):
            self.my_setDriver('GV5', round(cons_wh / 1000.0, 3), 33, force=force_energy)
        else:
            self.my_setDriver('GV5', None, 25, force=force_energy)

        # GV6: Exported (produced) energy in kWh
        if isinstance(prod_wh, (int, float)):
            self.my_setDriver('GV6', round(prod_wh / 1000.0, 3), 33, force=force_energy)
        else:
            self.my_setDriver('GV6', None, 25, force=force_energy)

        producedWh, consumerWh = self.span_panel.get1HourAverage(self.circuit)
        if isinstance(producedWh, (int, float)) and isinstance(consumerWh, (int, float)):            
            self.my_setDriver('GV7', -round((producedWh - consumerWh), 1), 119, force=force_energy)
        else:
            self.my_setDriver('GV7', None, 25, force=force_energy)

        producedWh, consumerWh = self.span_panel.get24HourAverage(self.circuit)   
        if isinstance(producedWh, (int, float)) and isinstance(consumerWh, (int, float)):                                  
            self.my_setDriver('GV8', -round((producedWh - consumerWh), 1), 119, force=force_energy) 
        else:
            self.my_setDriver('GV8', None, 25, force=force_energy)           

        if energy_time is not None:
            self.my_setDriver('GV9', energy_time, 151, force=force_energy)  

    def ISYupdate (self, command):
        logging.debug('ISY-update called')
        self.update_data(force=True)
        self.updateISYdrivers(force=True)

    def set_breaker(self, command):
        logging.debug(f'set_breaker called: {command}')
        if 'query' in command:
            state = int(command['query']['openclose.uom25'])
            if (0 == state):
                res =  self.span_panel.set_breaker_state(self.circuit, 'CLOSED')
            else:
                res = self.span_panel.set_breaker_state(self.circuit, 'OPEN')
            if res:
                self.my_setDriver('GV2', state, 25, force=True)

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
                self.my_setDriver('GV1', priority, 25, force=True)

    id = 'spancircuit'
    commands = {    
                'UPDATE'    : ISYupdate, 
                'OPENCLOSE' : set_breaker,
                #'PRIORITY'  : set_priority  Not workling yet - generates internal error
                }
    '''
        <st id="ST" editor="W" /> Instantaneous Power (W)
        <st id="GV1" editor="PRIORITY" /> Circuit Priority
        <st id="GV2" editor="OPENCLOSE" /> Circuit Relay State
        <st id="GV4" editor="UTIME" /> Power Measurement Time
        <st id="GV5" editor="KWH" /> Imported Energy
        <st id="GV6" editor="KWH" /> Exported Energy
        <st id="GV7" editor="WH" /> Energy last hour
        <st id="GV8" editor="WH" /> Energy last 24 hours
        <st id="GV9" editor="UTIME" /> Energy Measurement Time
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

    
