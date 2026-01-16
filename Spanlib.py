

import requests
import time
import json
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
        self.SAVE_TO_FILE = True

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
            logging.error(f'EXCEPTION: update_battery_info: {e}')
            return(None)

    def update_Accum_Energy(self, breaker_id = None, save_to_file = False):
        logging.debug(f'update_Accum_Energy {breaker_id}')
        if self.span_data.get('circuit_info') is None:
            return

        if breaker_id == None:
            for breaker_id in self.span_data['circuit_info']:
                self.update_Accum_EnergyBreaker(breaker_id)
        else:
            self.update_Accum_EnergyBreaker(breaker_id)

        if save_to_file:
            f = open(str(self.IP_address)+'.json', 'a+')
            current_time = time.localtime()
            time_string = time.strftime("%Y-%m-%d %H:%M:%S", current_time)
            f.write('\n\v'+time_string)            
            f.write(str(json.dumps( self.accum_data, indent=4, separators=(',', ': '))))
            f.close()
            f = open(str(self.IP_address)+'.cvs', 'w')
            f.write('breaker, update_time,consumedWh,producedWh\n')
            for breaker in self.accum_data:
                for data_time  in self.accum_data[breaker]:
                    f.write(str(breaker)+','+str(data_time)+','+str(self.accum_data[breaker][data_time]['consumedWh'])+','+str(self.accum_data[breaker][data_time]['producedWh'])+'\n')
            f.close()
            


    def update_Accum_EnergyBreaker(self, breaker_id ):
        try:
            logging.debug('update_Accum_EnergyBreaker - begin {} {}'.format(breaker_id,json.dumps( self.span_data['circuit_info'], indent=4, separators=(',', ': ') )))        
            hourSec = 3600 # 60*60
            daySec = 86400 # 60*60*24
            #logging.debug(f'update_Accum_Energy {breaker_id}')
        except KeyError as e:
            update_time = time.time()
            produced_energy = 0 
            consumed_energy =  0
            logging.debug('update_Accum_EnergyBreaker - key error {} {}'.format(breaker_id,json.dumps( self.span_data['circuit_info'], indent=4, separators=(',', ': ') )))        

        if breaker_id not in self.accum_data:
            self.accum_data[breaker_id] = {}

        # check if time is not update - only update if time changed  - Need to add 
        
        self.accum_data[breaker_id][update_time]={'update_time':update_time,'producedWh':produced_energy, 'consumedWh':consumed_energy}
        time_1_hour = update_time - hourSec #60*60
        time_24_hour = update_time - daySec #60*60*24
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
                if (abs(saved_time - time_1_hour) < abs(t_1hour-time_1_hour)):
                    t_1hour = saved_time
                    prod_1_hour = self.accum_data[breaker_id][saved_time]['producedWh']
                    cons_1_hour = self.accum_data[breaker_id][saved_time]['consumedWh']
                if (abs(saved_time - time_24_hour) < abs(t_24hour-time_24_hour)):
                    t_24hour = saved_time
                    prod_24_hour = self.accum_data[breaker_id][saved_time]['producedWh']
                    cons_24_hour = self.accum_data[breaker_id][saved_time]['consumedWh']
        except KeyError as e:
            logging.error(f'ERROR UPDATE ACCUM ENERY {e}')
        try:
            delete_list = []
            #logging.debug(f'start delete: {int(time.time())} - {self.accum_data[breaker_id]}')
            for saved_time in self.accum_data[breaker_id]:
                logging.debug(f'update time {saved_time}')
                if saved_time < t_24hour:
                    delete_list.append(self.accum_data[breaker_id][saved_time])
            #logging.debug(f'deletelist: {delete_list}')
            for indx, meas_data in enumerate(delete_list):
                #logging.debug(f'remove befor1 {meas_data}, {int(time.time())-daySec} ')
                #logging.debug('remove before2 {}'.format(meas_data['update_time']))
                del self.accum_data[breaker_id][meas_data['update_time']]
                logging.debug(f'remove meas {meas_data} ')
        except Exception as e:
            logging.error(f'Exception delete data {e}')
        #logging.debug(f'size of accum_data {len(self.accum_data[breaker_id])}')


        try:
            if  update_time != t_1hour and hour_ok:
                self.span_data['circuit_info'][breaker_id]['prod_1hour'] = (produced_energy-prod_1_hour)*3600/(update_time-t_1hour)
                self.span_data['circuit_info'][breaker_id]['cons_1hour'] = (consumed_energy-cons_1_hour)*3600/(update_time-t_1hour)
                #logging.debug(f'{breaker_id} 1 hour average: prod {produced_energy} - {prod_1_hour} - cons {consumed_energy} - {cons_1_hour} - time {update_time-t_1hour}')
            else:
                self.span_data['circuit_info'][breaker_id]['prod_1hour'] = None
                self.span_data['circuit_info'][breaker_id]['cons_1hour'] = None
            if  update_time != t_24hour and day_ok:
                self.span_data['circuit_info'][breaker_id]['prod_24hour'] = (produced_energy-prod_24_hour)*24*3600/(update_time-t_24hour)
                self.span_data['circuit_info'][breaker_id]['cons_24hour'] = (consumed_energy-cons_24_hour)*24*3600/(update_time-t_24hour)
                #logging.debug(f'{breaker_id}  24 hour average: prod {produced_energy} - {prod_24_hour} - cons {consumed_energy} - {cons_24_hour} - time {update_time-t_24hour}')
            else:
                self.span_data['circuit_info'][breaker_id]['prod_24hour'] = None
                self.span_data['circuit_info'][breaker_id]['cons_24hour'] = None
        except Exception as e:
            logging.error(f'Exception calculate averages {e}')

            
    def get1HourAverage(self, breaker_id):
        logging.debug(f'get1HourAverage {breaker_id}')
        #logging.debug('{} prod : {}, cons {}'.format(breaker_id, self.span_data['circuit_info'][breaker_id]['prod_1hour'], self.span_data['circuit_info'][breaker_id]['cons_1hour']))
        return(self.span_data['circuit_info'][breaker_id]['prod_1hour'], self.span_data['circuit_info'][breaker_id]['cons_1hour'] )

    def get24HourAverage(self, breaker_id):
        logging.debug(f'get24HourAverage {breaker_id}')
        return(self.span_data['circuit_info'][breaker_id]['prod_24hour'], self.span_data['circuit_info'][breaker_id]['cons_24hour'] )


    def update_panel_breaker_info(self, breaker_id):
        try:
            code, breaker_info = self.getSpanBreakerInfo(breaker_id)
            if code == 200:
               self.span_data['circuit_info'][breaker_id] = breaker_info
               self.update_Accum_EnergyBreaker(breaker_id)
            else:
                self.span_data['circuit_info'][breaker_id]  = None
            return(code )
        except Exception as e:
            logging.error(f'EXCEPTION: update_panel_breaker_info: {e}')
            return(None)


    def update_critical_span_data(self):
        logging.debug(f'update_critical_span_data ({self.IP_address})')
        #self.update_panel_status()
        #logging.debug('panel status {}'.format(self.span_data['status']))
        self.update_panel_info()
        logging.debug('panel info {}'.format(self.span_data['panel_info']))
        self.update_battery_info()
        logging.debug('battery info {}'.format(self.span_data['battery_info']))
        #self.update_circuit_info()
        #logging.debug('circuit info {}'.format(self.span_data['circuit_info']))        
        self.update_Accum_Energy(None, True)


    def update_span_data(self):
        logging.debug(f'update_span_data ({self.IP_address})')
        self.update_panel_status()
        logging.debug('panel status {}'.format(self.span_data['status']))
        self.update_panel_info()
        logging.debug('panel info {}'.format(self.span_data['panel_info']))
        self.update_battery_info()
        logging.debug('battery info {}'.format(self.span_data['battery_info']))
        self.update_circuit_info()
        logging.debug('circuit info {}'.format(self.span_data['circuit_info']))        
        self.update_Accum_Energy(None, True)

    def get_panel_door_state(self):
        logging.debug('get_panel_door_state')
        try:
            return(self.span_data['status']['system']['doorState'])
        except KeyError as e:
            return(None)
        

    def get_battery_percentage(self):
        logging.debug('get_battery_percentage')
        #logging.debug('data {}'.format(self.span_data['battery_info']))
        try:
            return(self.span_data['battery_info']['soe']['percentage'])
        except KeyError as e:
            return(None)


    def get_main_panel_breaker_state(self):
        logging.debug('get_main_panel_breaker_state')
        #logging.debug('data {}'.format(self.span_data['panel_info']))
        try:
            return(self.span_data['panel_info']['mainRelayState'])
        except KeyError as e:
            return(None)    


    def get_grid_state(self):
        logging.debug('get_grid_state')
        #logging.debug('data {}'.format(self.span_data['panel_info']))
        try:
            return(self.span_data['panel_info']['dsmGridState'])
        except KeyError as e:
            return(None)    


    def get_dms_state(self):        
        logging.debug('get_dms_state')
        logging.debug('data {}'.format(self.span_data['panel_info']))
        try:
            return(self.span_data['panel_info']['dsmState'])
        
        except KeyError as e:
            return(None)    


    def get_dms_run_config(self):    
        logging.debug('get_dms_run_config')
        logging.debug('data {}'.format(self.span_data['panel_info']))
        try:
            return(self.span_data['panel_info']['currentRunConfig'])
        except KeyError as e:
            return(None)    


    def get_instant_grid_power(self):         
        logging.debug('get_instant_grid_power')
        #logging.debug('data {}'.format(self.span_data['panel_info']))
        try:
            return(self.span_data['panel_info']['instantGridPowerW'])
        except KeyError as e:
            return(None)    

    def get_feedthrough_power(self):              
        logging.debug('get_feedthrough_power')
        #logging.debug('data {}'.format(self.span_data['panel_info']))
        try:
            return(self.span_data['panel_info']['feedthroughPowerW'] )
        except KeyError as e:
            return(None)    


    def get_breaker_state(self, breaker_id):
        logging.debug(f'get_breaker_state {breaker_id}')
        #logging.debug('data {}'.format(self.span_data['circuit_info'][breaker_id]))
        try:
            return(self.span_data['circuit_info'][breaker_id]['relayState'] )
        except KeyError as e:
            return(None)    

    def get_breaker_priority(self, breaker_id):
        logging.debug(f'get_breaker_priority {breaker_id}')
        #logging.debug('data {}'.format(self.span_data['circuit_info'][breaker_id]))
        try:
            return(self.span_data['circuit_info'][breaker_id]['priority'] )
        except KeyError as e:
            return None    


    def get_breaker_instant_power(self, breaker_id):
        logging.debug(f'get_breaker_instant_power {breaker_id}')
        #logging.debug('data {}'.format(self.span_data['circuit_info'][breaker_id]))
        try:
            pwr = self.span_data['circuit_info'][breaker_id]['instantPowerW']
            meas_time = int(time.time() -self.span_data['circuit_info'][breaker_id]['instantPowerUpdateTimeS'])
            return pwr,  meas_time
        except Exception as e:
            return None, None    

    def get_breaker_energy_info(self, breaker_id):
        logging.debug(f'get_breaker_energy_info {breaker_id}')
        try:
            produced_energy =  self.span_data['circuit_info'][breaker_id]['producedEnergyWh']
            consumed_energy = self.span_data['circuit_info'][breaker_id]['consumedEnergyWh'] 
            meas_time = self.span_data['circuit_info'][breaker_id]['energyAccumUpdateTimeS']
            #logging.debug(f'{breaker_id} get_breaker_energy_info {produced_energy} {consumed_energy} {delay_time}')
            return produced_energy, consumed_energy, meas_time
        except Exception as e:
            return None, None, None  

    def set_breaker_state(self, breaker_id, state):
        logging.debug(f'set_breaker_state {breaker_id} {state}')
        code, return_data = self.setBreakerState(breaker_id, state)
        #logging.debug(f'return {code}, {return_data}')
        if code == 200:
            self.span_data['circuit_info'][breaker_id] = return_data
        return code == 200

    def set_breaker_priority(self, breaker_id, priority):
        logging.debug(f'set_breaker_priority {breaker_id} {priority}')
        code, return_data = self.setBreakerPriority(breaker_id, priority)
        #logging.debug(f'return {code}, {return_data}')
        if code == 200:
            self.span_data['circuit_info'][breaker_id] = return_data
        return  code == 200


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
