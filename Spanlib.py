

import requests
import time
import urllib.parse
from datetime import datetime, timezone

try:
    from udi_interface import LOGGER, Custom, OAuth
    logging = LOGGER
    Custom = Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)

class SpanAccess(object):
    from  udiLib import random_string

    def __init__ (self, IPaddress, token):
        self.IP_address = IPaddress
        self.accessToken = token
        
        self.yourApiEndpoint = f'http://{self.IP_address}/api/v1'
        self.STATUS      = '/status'
        #self.SPACES      = '/spaces'
        self.CIRCUITS    = '/circuits'
        self.PANEL       = '/panel'
        self.REGISTER    = '/register'
        self.span_data = {}


    def update_panel_status(self):
        try:
            code, status = self.getSpanStatusInfo()
            if code == 200:
                self.span_data['status'] = status                
                return(ConnectionAbortedError)
            else:
                self.span_data['status'] = None
            return(code)
        except Exception as e:
            logging.error(f'EXCEPTION: update_panel_status: {e}')
            return(None)

    def update_panel_info(self):
        try:
            code, panel = self.getSpanPanelInfo()
            if code == 200:
               self.span_data['panel_info'] = panel
            else:
                self.span_data['panel_info'] = None
            return(code )
        except Exception as e:
            logging.error(f'EXCEPTION: update_panel_info: {e}')
            return(None)

    def update_battery_info(self):
        try:
            code, battery = self.getSpanBatteryInfo()
            if code == 200:
               self.span_data['battery_info'] = battery
            else:
                self.span_data['battery_info'] = None
            return(code )
        except Exception as e:
            logging.error(f'EXCEPTION: update_battery_info: {e}')
            return(None)
        

    def update_circuit_info(self):
        try:
            code, circuits = self.getSpanCircuitsInfo()
            if code == 200:
               self.span_data['circuit_info'] = circuits
            else:
                self.span_data['circuit_info'] =  None
            return(code )
        except Exception as e:
            logging.error(f'EXCEPTION: update_battery_info: {e}')
            return(None)
                
    def update_panel_breaker_info(self, breaker_id):
        try:
            code, breaker_info = self.getSpanBreakerInfo(breaker_id)
            if code == 200:
               self.span_data['circuit_info'][breaker_id] = breaker_info
            else:
                self.span_data['circuit_info'][breaker_id]  = None
            return(code )
        except Exception as e:
            logging.error(f'EXCEPTION: update_panel_breaker_info: {e}')
            return(None)

    def update_span_data(self):
        logging.debug(f'updateSpanData ({self.IP_address})')
        self.update_panel_status()
        logging.debug('panel status {}'.format(self.span_data['status']))
        self.update_panel_info()     
        logging.debug('panel info {}'.format(self.span_data['panel_info']))
        self.update_battery_info()
        logging.debug('battery info {}'.format(self.span_data['battery_info']))
        self.update_circuit_info()        
        logging.debug('circuit info {}'.format(self.span_data['circuit_info']))

    def get_panel_door_state(self):
        logging.debug('get_panel_door_state')
        try:
            return(self.span_data['status']['system']['doorState'])
        except Exception as e:
            return(None)
        

    def get_battery_percentage(self):
        logging.debug('get_battery_percentage')
        logging.debug('data {}'.format(self.span_data['battery_info']))
        try:
            return(self.span_data['battery_info']['soe']['percentage'])
        except Exception as e:
            return(None)


    def get_main_panel_breaker_state(self):
        logging.debug('get_main_panel_breaker_state')
        logging.debug('data {}'.format(self.span_data['panel_info']))
        try:
            return(self.span_data['panel_info']['mainRelayState'])
        except Exception as e:
            return(None)    


    def get_grid_state(self):
        logging.debug('get_grid_state')
        logging.debug('data {}'.format(self.span_data['panel_info']))
        try:
            return(self.span_data['panel_info']['dsmGridState'])
        except Exception as e:
            return(None)    


    def get_dms_state(self):        
        logging.debug('get_dms_state')
        logging.debug('data {}'.format(self.span_data['panel_info']))
        try:
            return(self.span_data['panel_info']['dsmState'])
        
        except Exception as e:
            return(None)    


    def get_dms_run_config(self):    
        logging.debug('get_dms_run_config')
        logging.debug('data {}'.format(self.span_data['panel_info']))
        try:
            return(self.span_data['panel_info']['currentRunConfig'])
        except Exception as e:
            return(None)    


    def get_instant_grid_power(self):         
        logging.debug('get_instant_grid_power')
        logging.debug('data {}'.format(self.span_data['panel_info']))
        try:
            return(self.span_data['panel_info']['instantGridPowerW'])
        except Exception as e:
            return(None)    

    def get_feedthrough_power(self):              
        logging.debug('get_feedthrough_power')
        logging.debug('data {}'.format(self.span_data['panel_info']))
        try:
            return(self.span_data['panel_info']['feedthroughPowerW'] )
        except Exception as e:
            return(None)    


    def get_breaker_state(self, breaker_id):
        logging.debug(f'get_breaker_state {breaker_id}')
        logging.debug('data {}'.format(self.span_data['circuit_info'][breaker_id]))
        try:
            return(self.span_data['circuit_info'][breaker_id]['relayState'] )
        except Exception as e:
            return(None)    

    def get_breaker_priority(self, breaker_id):
        logging.debug(f'get_breaker_priority {breaker_id}')
        logging.debug('data {}'.format(self.span_data['circuit_info'][breaker_id]))
        try:
            return(self.span_data['circuit_info'][breaker_id]['priority'] )
        except Exception as e:
            return(None)    


    def get_breaker_instant_power(self, breaker_id):
        logging.debug(f'get_breaker_instant_power {breaker_id}')
        logging.debug('data {}'.format(self.span_data['circuit_info'][breaker_id]))
        try:
            pwr = self.span_data['circuit_info'][breaker_id]['instantPowerW']
            delay_time = int(time.time() -self.span_data['circuit_info'][breaker_id]['instantPowerUpdateTimeS'])
            return(pwr,  delay_time )
        except Exception as e:
            return(None)    

    def get_breaker_energy_info(self, breaker_id):
        logging.debug('get_breaker_energy_info {breaker_id}')
        try:
            produced_energy =  self.span_data['circuit_info'][breaker_id]['producedEnergyWh']
            consumed_energy = self.span_data['circuit_info'][breaker_id]['consumedEnergyWh'] 
            delay_time = int(time.time() -self.span_data['circuit_info'][breaker_id]['energyAccumUpdateTimeS'])
            return(produced_energy, consumed_energy, delay_time)
        except Exception as e:
            return(None)    

    def set_breaker_state(self, breaker_id, state):
        logging.debug(f'set_breaker_state {breaker_id} {state}')
        code, return_data = self.setBreakerState(breaker_id, state)
        logging.debug(f'return {code}, {return_data}')
        if code == 200:
            self.span_data['circuit_info'][breaker_id] = return_data

    def set_breaker_priority(self, breaker_id, priority):
        logging.debug(f'set_breaker_priority {breaker_id} {priority}')
        code, return_data = self.setBreakerPriority(breaker_id, priority)
        logging.debug(f'return {code}, {return_data}')
        if code == 200:
            self.span_data['circuit_info'][breaker_id] = return_data



############################

    def setBreakerState(self, id, state):
        logging.debug(f'setBreakerState {id}  {state}')
        if state in ['OPEN', 'CLOSED']:
            data =  {
                    'relay_state_in':{'relayState':state}
                    }                
            code, breaker_info = self._callApi('POST', '/circuits/'+str(id), data)
            return(code, breaker_info)
        else:
            return None, None

    def setBreakerPriority(self, id, priority):
        logging.debug(f'setBreakerState {id}  {priority}')
        if priority in ['MUST_HAVE', 'NICE_TO_HAVE', 'NOT_ESSENTIAL' ]:
            data =  {
                    'relay_state_in':{'relayState':priority}
                    }                
            code, breaker_info = self._callApi('POST', '/circuits/'+str(id), data)
            return(code, breaker_info)
        else:
            return None, None


    def getAccessToken(self):
        logging.debug(f'getAccessToken ({self.IP_address})')        
        return(self.accessToken)

    def putAccessToken(self, accessToken):
        self.accessToken = accessToken
    
    def getSpanCircuitsInfo(self):
        logging.debug(f'getSpanCircuitsInfo ({self.IP_address})')        
        code, circuits = self._callApi('GET', '/circuits')
        if code == 200:
            return(code, circuits['circuits'])
        else:
            return(code, circuits)
    

    def getSpanBreakerInfo(self, id):
        logging.debug(f'getSpanBreakerInfo ({self.IP_address})')        
        code, circuitInf = self._callApi('GET', '/circuits/'+str(id))
        return(code, circuitInf)
    

    def getSpanStatusInfo(self):
        logging.debug(f'getSpanStatusIndo ({self.IP_address})')
        code, status = self._callApi('GET', '/status')
        return(code, status)
    
    def getSpanPanelInfo(self):
        logging.debug(f'getSpanPanelInfo ({self.IP_address})')
        code, panel = self._callApi('GET', '/panel')
        return(code, panel)

    def getSpanBatteryInfo(self):
        logging.debug(f'getSpanBatteryInfo ({self.IP_address})')
        code, battery_perc = self._callApi('GET', '/storage/soe')
        return(code, battery_perc)

    def getSpanClientInfo(self):
        logging.debug(f'getSpanClientInfo ({self.IP_address})')
        code, clients = self._callApi('GET', '/auth/clients')
        return(code, clients)



  


    def _callApi(self, method='GET', url=None, body=None):
        # When calling an API, get the access token (it will be refreshed if necessary)
        try:
            accessToken = self.getAccessToken()
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            #self.poly.Notices['auth'] = 'Please initiate authentication'
            return
        if accessToken is None:
            logging.error('Access token is not available')
            return None

        if url is None:
            logging.error('url is required')
            return None

        completeUrl = self.yourApiEndpoint + url

        headers = {
            'Authorization': f"Bearer { accessToken }"
        }

        if method in [ 'PATCH', 'POST'] and body is None:
            logging.error(f"body is required when using { method } { completeUrl }")
        logging.debug(' call info url={}, header= {}, body = {}'.format(completeUrl, headers, body))

        try:
            if method == 'GET':
                response = requests.get(completeUrl, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(completeUrl, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(completeUrl, headers=headers, json=body)
            elif method == 'POST':
                response = requests.post(completeUrl, headers=headers, json=body)
            elif method == 'PUT':
                response = requests.put(completeUrl, headers=headers)

            response.raise_for_status()
            try:
                return response.status_code, response.json()
            except requests.exceptions.JSONDecodeError:
                return response.status_code, response.text

        except requests.exceptions.HTTPError as error:
            logging.error(f"Call { method } { completeUrl } failed: { error }")
            return response.status_code,  error
