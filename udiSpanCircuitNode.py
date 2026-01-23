#!/usr/bin/env python3

#import time

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=30)



class udiSpanCircuitNode(udi_interface.Node):
    from  udiLib import node_queue, wait_for_node_done, openClose2ISY, priority2ISY, mask2key, bool2ISY, round2ISY, my_setDriver

    def __init__(self, polyglot, primary, address, name, span_access, circuit):
        #super(teslaPWStatusNode, self).__init__(polyglot, primary, address, name)
        logging.info(f'_init_ Span Circuit Node {name}')
        self.poly = polyglot
        self.span_panel = span_access
        self.circuit = circuit
        
        self.node_ok = False
        self.address = address
        self.primary = primary
        self.name = name
        self.n_queue = []
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.START, self.start, address)

        self.poly.ready()
        self.poly.addNode(self)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)

        

        
    def start(self):   
        logging.debug(f'Start Span Circuit node {self.name}')

        self.circuit_data = self.span_panel.getSpanBreakerInfo(self.circuit )
        self.updateISYdrivers()
        
        
        self.node_ok = True

    def stop(self):
        logging.debug('stop - Cleaning up')
    
    def node_ready(self):
        return(self.node_ok)

    def update_data(self):
        code = self.span_panel.update_panel_breaker_info(self.circuit )

    def updateISYdrivers(self):
        logging.debug(f'SpanCircuit updateISYdrivers {self.name}')
        #logging.debug(f'data: {self.span_panel.span_data}')
        self.my_setDriver('ST', self.openClose2ISY(self.span_panel.get_breaker_state(self.circuit)))
        self.my_setDriver('GV1', self.priority2ISY(self.span_panel.get_breaker_priority(self.circuit)))
        pwr, meas_time = self.span_panel.get_breaker_instant_power(self.circuit)
        self.my_setDriver('GV2', round(-pwr, 1), 73)
        self.my_setDriver('GV4', meas_time, 151)  # Needs to be updated
        imp_wh, exp_wh, meas_time = self.span_panel.get_breaker_energy_info(self.circuit)
        self.my_setDriver('GV5', round(imp_wh, 1), 119 ) 
        self.my_setDriver('GV6', round(exp_wh, 1), 119 )   
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
        self.my_setDriver('GV9', meas_time, 151 )  

    def ISYupdate (self, command):
        logging.debug('ISY-update called')
        #self.update_PW_data(self.site_id, 'all')
        self.update_data()
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
                self.my_setDriver('ST', state)


    def set_priority(self, command):
        logging.debug(f'set_priority called: {command}')
        if 'query' in command:
            priority = int(command['query']['priority.uom25'])
            if (0 == priority):
                res =  self.span_panel.set_breaker_priority(self.circuit, 'MUST_HAVE')
            elif (1 == priority):
                res =  self.span_panel.set_breaker_priority(self.circuit, 'NICE _O_HAVE')
            else:
                res = self.span_panel.set_breaker_priority(self.circuit, 'NOT_ESSENTIAL')
            if res:
                self.my_setDriver('ST', priority)   



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
            {'driver': 'ST', 'value': 99, 'uom': 25},  #online         
            #{'driver': 'GV0', 'value': 0, 'uom': 51},       
            {'driver': 'GV1', 'value': 0, 'uom': 25},
            {'driver': 'GV2', 'value': 0, 'uom': 73},  
            #{'driver': 'GV3', 'value': 0, 'uom': 57}, 
            {'driver': 'GV4', 'value': 0, 'uom': 151},  

            {'driver': 'GV5', 'value': 99, 'uom': 119},  
            {'driver': 'GV6', 'value': 99, 'uom': 119},  
            {'driver': 'GV7', 'value': 99, 'uom': 119},  
            {'driver': 'GV8', 'value': 99, 'uom': 119}, 

            {'driver': 'GV9', 'value': 0, 'uom': 151},           

            ]

    
