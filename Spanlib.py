

import requests
import time
import json
import os
#from datetime import datetime, timezone

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
        #self.STATUS      = '/status'
        #self.SPACES      = '/spaces'
        ##self.CIRCUITS    = '/circuits'
        #self.PANEL       = '/panel'
        #self.REGISTER    = '/register'
        self.span_data = {}
        self.accum_data = {}
        self.SAVE_TO_FILE = False
        self.load_accum_data()

    def update_panel_status(self):
        try:
            code, status = self.getSpanStatusInfo()
            if code == 200:
                self.span_data['status'] = status                
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
                if self.SAVE_TO_FILE:
                    f = open('Panel_data.json', 'a+')
                    current_time = time.localtime()
                    time_string = time.strftime("%Y-%m-%d %H:%M:%S", current_time)
                    f.write('\n\v'+time_string)
                    f.write(str(json.dumps( panel, indent=4, separators=(',', ': '))))
                    f.close()
                    #f = open(str(self.IP_address)+'.cvs', 'w')
                    #f.write('breaker, update_time,consumedWh,producedWh\n')
                    #for breaker in self.accum_data:
                    #    for data_time  in self.accum_data[breaker]:
                    #        f.write(str(breaker)+','+str(data_time)+','+str(self.accum_data[breaker][data_time]['consumedWh'])+','+str(self.accum_data[breaker][data_time]['producedWh'])+'\n')
                    #f.close()
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
                if self.SAVE_TO_FILE:
                    f = open('battery_data.json', 'a+')
                    current_time = time.localtime()
                    time_string = time.strftime("%Y-%m-%d %H:%M:%S", current_time)
                    f.write('\n\v'+time_string)                    
                    f.write(str(json.dumps( battery, indent=4, separators=(',', ': '))))
                    f.close()
               
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
                if self.SAVE_TO_FILE:
                    f = open('circuitdata.json', 'a+')
                    current_time = time.localtime()
                    time_string = time.strftime("%Y-%m-%d %H:%M:%S", current_time)
                    f.write('\n\v'+time_string)                    
                    f.write(str(json.dumps( circuits, indent=4, separators=(',', ': '))))
                    f.close()
            else:
                self.span_data['circuit_info'] =  None
            return(code )
        except Exception as e:
            logging.error(f'EXCEPTION: update_circuit_info: {e}')
            return(None)

    def load_accum_data(self):
        filename = f'accum_data_{self.IP_address}.json'
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    data = json.load(f)
                    self.accum_data = {}
                    if isinstance(data, dict):
                        for breaker_id, records in data.items():
                            self.accum_data[breaker_id] = {}
                            if isinstance(records, dict):
                                for k, v in records.items():
                                    t = int(k) if str(k).isdigit() else k
                                    self.accum_data[breaker_id][t] = v
                logging.info(f'Loaded accum_data for {self.IP_address} from {filename} ({len(self.accum_data)} breakers)')
        except Exception as e:
            logging.error(f'Error loading accum_data from {filename}: {e}')

    def save_accum_data(self):
        filename = f'accum_data_{self.IP_address}.json'
        try:
            if self.accum_data:
                with open(filename, 'w') as f:
                    json.dump(self.accum_data, f, indent=2)
                logging.debug(f'Saved accum_data for {self.IP_address} to {filename}')
        except Exception as e:
            logging.error(f'Error saving accum_data to {filename}: {e}')

    def update_Accum_Energy(self, breaker_id = None, save_to_file = False):
        logging.debug(f'update_Accum_Energy {breaker_id}')
        if not isinstance(self.span_data.get('circuit_info'), dict):
            return

        if breaker_id is None:
            for b_id in list(self.span_data['circuit_info'].keys()):
                self.update_Accum_EnergyBreaker(b_id)
        else:
            self.update_Accum_EnergyBreaker(breaker_id)

        self.save_accum_data()

    def update_Accum_EnergyBreaker(self, breaker_id ):
        hourSec = 3600 # 60*60
        daySec = 86400 # 60*60*24
        try:
            circuit = (self.span_data.get('circuit_info') or {}).get(breaker_id) or {}
            update_time = circuit.get('energyAccumUpdateTimeS')
            produced_energy = circuit.get('producedEnergyWh')
            consumed_energy = circuit.get('consumedEnergyWh')
        except Exception as e:
            update_time = int(time.time())
            produced_energy = 0.0
            consumed_energy = 0.0
            logging.debug(f'update_Accum_EnergyBreaker - error getting energy for {breaker_id}: {e}')
            return

        if update_time is None:
            update_time = int(time.time())
        # Do NOT update time or accum data if no data or invalid timestamp occurs
        if (
            update_time is None
            or not isinstance(update_time, (int, float))
            or update_time <= 0
            or (produced_energy is None and consumed_energy is None)
        ):
            logging.debug(f'update_Accum_EnergyBreaker - no data or invalid timestamp for {breaker_id}, skipping')
            return

        update_time = int(update_time)
        if produced_energy is None:
            produced_energy = 0.0
        if consumed_energy is None:
            consumed_energy = 0.0

        if breaker_id not in self.accum_data:
            self.accum_data[breaker_id] = {}

        self.accum_data[breaker_id][update_time] = {'update_time': update_time, 'producedWh': produced_energy, 'consumedWh': consumed_energy}
        time_1_hour = update_time - hourSec
        time_24_hour = update_time - daySec
        t_1hour = update_time
        t_24hour = update_time
        prod_1_hour = produced_energy
        cons_1_hour = consumed_energy
        prod_24_hour = produced_energy
        cons_24_hour = consumed_energy
        hour_ok = False
        day_ok = False
        try:
            for saved_time in self.accum_data[breaker_id]:
                if saved_time <= time_1_hour:
                    hour_ok = True
                if saved_time <= time_24_hour:
                    day_ok = True
                if (abs(saved_time - time_1_hour) < abs(t_1hour - time_1_hour)):
                    t_1hour = saved_time
                    prod_1_hour = self.accum_data.get(breaker_id, {}).get(saved_time, {}).get('producedWh')
                    cons_1_hour = self.accum_data.get(breaker_id, {}).get(saved_time, {}).get('consumedWh')
                if (abs(saved_time - time_24_hour) < abs(t_24hour - time_24_hour)):
                    t_24hour = saved_time
                    prod_24_hour = self.accum_data.get(breaker_id, {}).get(saved_time, {}).get('producedWh')
                    cons_24_hour = self.accum_data.get(breaker_id, {}).get(saved_time, {}).get('consumedWh')
        except Exception as e:
            logging.error(f'ERROR UPDATE ACCUM ENERGY {e}')

        try:
            if day_ok:
                delete_list = []
                for saved_time in list(self.accum_data[breaker_id].keys()):
                    if saved_time < t_24hour:
                        delete_list.append(saved_time)
                for st in delete_list:
                    del self.accum_data[breaker_id][st]
        except Exception as e:
            logging.error(f'Exception delete data {e}')

        try:
            circuit_entry = (self.span_data.get('circuit_info') or {}).get(breaker_id)
            if isinstance(circuit_entry, dict):
                dt_1h = update_time - t_1hour
                if (dt_1h >= 60 or (dt_1h > 0 and hour_ok)) and prod_1_hour is not None and cons_1_hour is not None:
                    circuit_entry['prod_1hour'] = (produced_energy - prod_1_hour) * 3600 / dt_1h
                    circuit_entry['cons_1hour'] = (consumed_energy - cons_1_hour) * 3600 / dt_1h
                else:
                    circuit_entry['prod_1hour'] = None
                    circuit_entry['cons_1hour'] = None

                dt_24h = update_time - t_24hour
                if (dt_24h >= 60 or (dt_24h > 0 and day_ok)) and prod_24_hour is not None and cons_24_hour is not None:
                    circuit_entry['prod_24hour'] = (produced_energy - prod_24_hour) * 24 * 3600 / dt_24h
                    circuit_entry['cons_24hour'] = (consumed_energy - cons_24_hour) * 24 * 3600 / dt_24h
                else:
                    circuit_entry['prod_24hour'] = None
                    circuit_entry['cons_24hour'] = None
        except Exception as e:
            logging.error(f'Exception calculate averages {e}')

            
    def get1HourAverage(self, breaker_id):
        logging.debug(f'get1HourAverage {breaker_id}')
        circuit = (self.span_data.get('circuit_info') or {}).get(breaker_id) or {}
        return (circuit.get('prod_1hour'), circuit.get('cons_1hour'))

    def get24HourAverage(self, breaker_id):
        logging.debug(f'get24HourAverage {breaker_id}')
        circuit = (self.span_data.get('circuit_info') or {}).get(breaker_id) or {}
        return (circuit.get('prod_24hour'), circuit.get('cons_24hour'))

    def update_panel_breaker_info(self, breaker_id):
        try:
            code, breaker_info = self.getSpanBreakerInfo(breaker_id)
            if not isinstance(self.span_data.get('circuit_info'), dict):
                self.span_data['circuit_info'] = {}
            if code == 200:
                self.span_data['circuit_info'][breaker_id] = breaker_info
                self.update_Accum_EnergyBreaker(breaker_id)
            else:
                self.span_data['circuit_info'][breaker_id] = None
            return code
        except Exception as e:
            logging.error(f'EXCEPTION: update_panel_breaker_info: {e}')
            return None


    def update_critical_span_data(self):
        logging.debug(f'update_critical_span_data ({self.IP_address})')
        #self.update_panel_status()
        #logging.debug('panel status {}'.format(self.span_data['status']))
        self.update_panel_info()
        logging.debug('panel info {}'.format(self.span_data.get('panel_info')))
        self.update_battery_info()
        logging.debug('battery info {}'.format(self.span_data.get('battery_info')))
        #self.update_circuit_info()
        #logging.debug('circuit info {}'.format(self.span_data.get('circuit_info')))        
        self.update_Accum_Energy(None, True)


    def update_span_data(self):
        logging.debug(f'update_span_data ({self.IP_address})')
        self.update_panel_status()
        logging.debug('panel status {}'.format(self.span_data.get('status')))
        self.update_panel_info()
        logging.debug('panel info {}'.format(self.span_data.get('panel_info')))
        self.update_battery_info()
        logging.debug('battery info {}'.format(self.span_data.get('battery_info')))
        self.update_circuit_info()
        logging.debug('circuit info {}'.format(self.span_data.get('circuit_info')))        
        self.update_Accum_Energy(None, True)

    def get_panel_door_state(self):
        logging.debug('get_panel_door_state')
        try:
            return (self.span_data.get('status') or {}).get('system', {}).get('doorState')
        except Exception as e:
            return None

    def get_battery_percentage(self):
        logging.debug('get_battery_percentage')
        try:
            return (self.span_data.get('battery_info') or {}).get('soe', {}).get('percentage')
        except Exception as e:
            return None

    def get_main_panel_breaker_state(self):
        logging.debug('get_main_panel_breaker_state')
        try:
            return (self.span_data.get('panel_info') or {}).get('mainRelayState')
        except Exception as e:
            return None    

    def get_grid_state(self):
        logging.debug('get_grid_state')
        try:
            return (self.span_data.get('panel_info') or {}).get('dsmGridState')
        except Exception as e:
            return None    

    def get_dms_state(self):        
        logging.debug('get_dms_state')
        try:
            return (self.span_data.get('panel_info') or {}).get('dsmState')
        except Exception as e:
            return None    

    def get_dms_run_config(self):    
        logging.debug('get_dms_run_config')
        try:
            return (self.span_data.get('panel_info') or {}).get('currentRunConfig')
        except Exception as e:
            return None    

    def get_instant_grid_power(self):         
        logging.debug('get_instant_grid_power')
        try:
            return (self.span_data.get('panel_info') or {}).get('instantGridPowerW')
        except Exception as e:
            return None    

    def get_feedthrough_power(self):              
        logging.debug('get_feedthrough_power')
        try:
            return (self.span_data.get('panel_info') or {}).get('feedthroughPowerW')
        except Exception as e:
            return None    

    def get_breaker_state(self, breaker_id):
        logging.debug(f'get_breaker_state {breaker_id}')
        try:
            return (self.span_data.get('circuit_info') or {}).get(breaker_id, {}).get('relayState')
        except Exception as e:
            return None    

    def get_breaker_priority(self, breaker_id):
        logging.debug(f'get_breaker_priority {breaker_id}')
        try:
            return (self.span_data.get('circuit_info') or {}).get(breaker_id, {}).get('priority')
        except Exception as e:
            return None    

    def get_breaker_instant_power(self, breaker_id):
        logging.debug(f'get_breaker_instant_power {breaker_id}')
        try:
            circuit = (self.span_data.get('circuit_info') or {}).get(breaker_id) or {}
            pwr = circuit.get('instantPowerW')
            meas_time = circuit.get('instantPowerUpdateTimeS')
            return pwr, int(meas_time) if meas_time is not None else None
            if (
                pwr is None
                or not isinstance(pwr, (int, float))
                or meas_time is None
                or not isinstance(meas_time, (int, float))
                or meas_time <= 0
            ):
                return (pwr if isinstance(pwr, (int, float)) else None), None
            return pwr, int(meas_time)
        except Exception as e:
            return None, None    

    def get_breaker_energy_info(self, breaker_id):
        logging.debug(f'get_breaker_energy_info {breaker_id}')
        try:
            circuit = (self.span_data.get('circuit_info') or {}).get(breaker_id) or {}
            produced_energy = circuit.get('producedEnergyWh')
            consumed_energy = circuit.get('consumedEnergyWh') 
            meas_time = circuit.get('energyAccumUpdateTimeS')
            return produced_energy, consumed_energy, int(meas_time) if meas_time is not None else None
            if (
                (produced_energy is None and consumed_energy is None)
                or meas_time is None
                or not isinstance(meas_time, (int, float))
                or meas_time <= 0
            ):
                return (
                    produced_energy if isinstance(produced_energy, (int, float)) else None,
                    consumed_energy if isinstance(consumed_energy, (int, float)) else None,
                    None,
                )
            return produced_energy, consumed_energy, int(meas_time)
        except Exception as e:
            return None, None, None  

    def set_breaker_state(self, breaker_id, state):
        logging.debug(f'set_breaker_state {breaker_id} {state}')
        code, return_data = self.setBreakerState(breaker_id, state)
        if code == 200:
            if not isinstance(self.span_data.get('circuit_info'), dict):
                self.span_data['circuit_info'] = {}
            self.span_data['circuit_info'][breaker_id] = return_data
        return code == 200

    def set_breaker_priority(self, breaker_id, priority):
        logging.debug(f'set_breaker_priority {breaker_id} {priority}')
        code, return_data = self.setBreakerPriority(breaker_id, priority)
        if code == 200:
            if not isinstance(self.span_data.get('circuit_info'), dict):
                self.span_data['circuit_info'] = {}
            self.span_data['circuit_info'][breaker_id] = return_data
        return code == 200


############################

    def setBreakerState(self, id, state):
        logging.debug(f'setBreakerState {id}  {state}')
        if state in ['OPEN', 'CLOSED']:
            data =  {
                    "relayStateIn":{"relayState":str(state)}
                    }                
            code, breaker_info = self._callApi('POST', '/circuits/'+str(id), data)
            return code, breaker_info
        else:
            return None, None

    def setBreakerPriority(self, id, priority):
        logging.debug(f'setBreakerState {id}  {priority}')
        if priority in ['MUST_HAVE', 'NICE_TO_HAVE', 'NOT_ESSENTIAL' ]:
            data =  {
                    "priorityIn":{"priority":str(priority)}
                    }                
            code, breaker_info = self._callApi('POST', '/circuits/'+str(id), data)
            return code, breaker_info
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
        if code == 200 and isinstance(circuits, dict):
            return(code, circuits.get('circuits', {}))
        else:
            return(code, circuits)
    

    def getSpanBreakerInfo(self, id):
        logging.debug(f'getSpanBreakerInfo ({self.IP_address})')        
        code, circuitInf = self._callApi('GET', '/circuits/'+str(id))
        return(code, circuitInf)
    

    def getSpanStatusInfo(self):
        logging.debug(f'getSpanStatusInfo ({self.IP_address})')
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
            return None, None
        if accessToken is None:
            logging.error('Access token is not available')
            return None, None

        if url is None:
            logging.error('url is required')
            return None, None

        completeUrl = self.yourApiEndpoint + url

        headers = {
            'Authorization': f"Bearer { accessToken }"
        }

        if method in [ 'PATCH', 'POST'] and body is None:
            logging.error(f"body is required when using { method } { completeUrl }")
        #logging.debug(' call info url={}, header= {}, body = {}'.format(completeUrl, headers, body))

        try:
            if method == 'GET':
                response = requests.get(completeUrl, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(completeUrl, headers=headers, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(completeUrl, headers=headers, json=body, timeout=10)
            elif method == 'POST':
                response = requests.post(completeUrl, headers=headers, json=body, timeout=10)
            elif method == 'PUT':
                response = requests.put(completeUrl, headers=headers, timeout=10)

            response.raise_for_status()
            try:
                return response.status_code, response.json()
            except requests.exceptions.JSONDecodeError:
                return response.status_code, response.text

        except requests.exceptions.HTTPError as error:
            status_code = getattr(response, 'status_code', None)
            logging.error(f"Call { method } { completeUrl } failed HTTP error: { error }")
            return status_code,  error
        except requests.exceptions.RequestException as error:
            logging.error(f"Call { method } { completeUrl } failed request exception: { error }")
            return None, error
        except Exception as error:
            logging.error(f"Call { method } { completeUrl } failed: { error }")
            return None, error
