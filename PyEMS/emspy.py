import sys
import datetime


class EmsPy:
    def __init__(self, ep_path, ep_idf_to_run, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc):
        #TODO figure out if threading and if this should be instance or class var (don't need every instance calling?)
        self.ep_path = ep_path
        sys.path.insert(0, ep_path)  # set path to E+
        from pyenergyplus.api import EnergyPlusAPI
        self.api = EnergyPlusAPI()  # instantiation of Python EMS API

        # instance important below
        self.state = self.api.state_manager.new_state()
        self.idf_file = ep_idf_to_run  # E+ idf file to simulation

        # Table of Contents for EMS sensor and actuators
        self.vars_tc = vars_tc
        self.int_vars_tc = int_vars_tc
        self.meters_tc = meters_tc
        self.actuators_tc = actuators_tc
        # create attributes of sensor and actuator .idf handles and data arrays
        self._init_ems_handles_and_data()  # creates ems_handle = int & ems_data = [] attributes
        self.got_ems_handles = False
        self.static_vars_gathered = False  # static (internal) variables, gather once

        # Table of Content for present weather data
        self.weather_tc = weather_tc
        self._init_weather_data()  # creates weather_data = [] attribute, useful for present/prior weather data tracking

        # timing
        self.actual_date_times = []
        self.actual_times = []
        self.current_times = []
        self.years = []
        self.months = []
        self.days = []
        self.hours = []
        self.minutes = []
        self.time_x = []
        # present simulation timesteps
        self.count = 0
        # TODO what/how to track?
        self.sys_ts = 0
        self.zone_ts = 1  # fluctuate from one to # of timesteps per hour TODO weather data dependent on this

    def _init_ems_handles_and_data(self):
        """
        Initialize all the instance attribute names given by the user for the sensors/actuators to be called
        """
        # set attribute handle names and data arrays given by user to None
        if self.vars_tc is not None:
            for var in self.vars_tc:
                setattr(self, var[0] + '_handle', None)
                setattr(self, var[0] + '_data', [])
        if self.int_vars_tc is not None:
            for int_var in self.int_vars_tc:
                setattr(self, int_var[0] + '_handle', None)
                setattr(self, int_var[0] + '_data', None)  # static val
        if self.meters_tc is not None:
            for meter in self.meters_tc:
                setattr(self, meter[0] + '_handle', None)
                setattr(self, meter[0] + '_data', [])
        if self.actuators_tc is not None:
            for actuator in self.actuators_tc:
                setattr(self, actuator[0] + '_handle', None)
                setattr(self, actuator[0] + '_data', [])

    def _init_weather_data(self):
        if self.weather_tc is not None:
            for weather_type in self.weather_tc:
                setattr(self, weather_type + '_data', [])

    def _set_ems_handles(self, state_arg):
        if self.vars_tc is not None:
            for var in self.vars_tc:
                setattr(self, var[0] + '_handle', self._get_handle('var', var))
        if self.int_vars_tc is not None:
            for int_var in self.int_vars_tc:
                setattr(self, int_var[0] + '_handle', self._get_handle('int_var', int_var))
        if self.meters_tc is not None:
            for meter in self.meters_tc:
                setattr(self, meter[0] + '_handle', self._get_handle('meter', meter))
        if self.actuators_tc is not None:
            for actuator in self.actuators_tc:
                setattr(self, actuator[0] + '_handle', self._get_handle('actuator', actuator))

    def _get_handle(self, ems_type: str, ems_obj):
        state = self.state
        datax = self.api.exchange
        try:
            handle = ""
            if ems_type is 'var':
                handle = datax.get_variable_handle(state,
                                                   ems_obj[1],  # var name
                                                   ems_obj[2])  # var key
            elif ems_type is 'int_var':
                handle = datax.get_internal_variable_handle(state,
                                                            ems_obj[1],  # int var name
                                                            ems_obj[2])  # int var key
            elif ems_type is 'meter':
                handle = datax.get_meter_handle(state,
                                                ems_obj[1])  # meter name
            elif ems_type is "actuator":
                handle = datax.get_actuator_handle(state,
                                                   ems_obj[1],  # component type
                                                   ems_obj[2],  # control type
                                                   ems_obj[3])  # actuator key
            # catch error handling by EMS E+
            if handle == -1:
                raise Exception(str(ems_obj) + ': Either Variable (sensor) or Internal Variable handle could not be'
                                                ' found. Please consult the .idf and/or your ToC')
            else:
                return handle
        except IndexError:
            raise IndexError(str(ems_obj) + f': This {ems_type} does not have all the required fields')

    def _update_time(self):
        state = self.state
        api = self.api
        # gather data
        year = api.exchange.year(state)
        month = api.exchange.month(state)
        day = api.exchange.day_of_month(state)
        hour = api.exchange.hour(state)
        minute = api.exchange.minutes(state)
        # set, append
        self.actual_date_times.append(api.exchange.actual_date_time(state))
        self.actual_times.append(api.exchange.actual_time(state))
        self.current_times.append(api.exchange.current_time(state))
        self.years.append(year)
        self.months.append(month)
        self.days.append(day)
        self.hours.append(hour)
        self.minutes.append(minute)
        # manage timestep tracking
        timedelta = datetime.timedelta()
        if hour >= 24.0:
            hour = 23.0
            timedelta += datetime.timedelta(hours=1)
        if minute >= 60.0:
            minute = 59
            timedelta += datetime.timedelta(minutes=1)
        dt = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute)
        dt += timedelta
        self.time_x.append(dt)
        # TODO update zone and sys timsteps

    def _update_ems_vals(self):
        state = self.state
        datax = self.api.exchange
        if self.vars_tc is not None:
            for var in self.vars_tc:
                data_i = datax.get_variable_value(state, getattr(self, var[0] + '_handle'))
                getattr(self, var[0] + '_data').append(data_i)
        if self.meters_tc is not None:
            for meter in self.meters_tc:
                data_i = datax.get_meter_value(state, getattr(self, meter[0] + '_handle'))
                getattr(self, meter[0] + '_data').append(data_i)
        if self.actuators_tc is not None:
            for actuator in self.actuators_tc:
                data_i = datax.get_actuator_value(state, getattr(self, actuator[0] + '_handle'))
                getattr(self, actuator[0] + '_data').append(data_i)
        # update static (internal) variables once
        if self.int_vars_tc is not None and not self.static_vars_gathered:
            for int_var in self.int_vars_tc:
                data_i = datax.get_internal_variable_value(state, getattr(self, int_var[0] + '_handle'))
                getattr(self, int_var[0] + '_data').append(data_i)
                self.static_vars_gathered = True

    def _update_weather_vals(self):
        # update and append present weather vals
        if self.weather_tc is not None:
            for weather_type in self.weather_tc:
                data_i = self._get_weather('today', weather_type, self.hours[-1], self.zone_ts)
                getattr(self, weather_type + '_data').append(data_i)

    def _get_weather(self, when: str, weather_type: str, hour: int, zone_ts: int):
        if weather_type is not 'sun_up':
            weather_dict = {
                'rain': 'is_raining',
                'snow': 'is_snowing',
                'precipitation': 'liquid_precipiation',
                'bar_pressure': 'barometric_pressure',
                'dew_point': 'outdoor_dew_point',
                'dry_bulb': 'outdoor_dry_buld',
                'rel_humidity': 'outdoor_relative_humidity',
                'wind_dir': 'wind_direction',
                'wind_speed': 'wind_speed',
                # simply add api weather relations
            }
            weather = weather_dict.get(weather_type)
            # TODO verify validity of getattr
            return getattr(self.api.exchange, when + '_weather_' + weather + '_at_time')(self.state, hour, zone_ts)
        elif weather_type is 'sun_up':
            return self.api.exchange.sun_is_up(self.state)

    def set_calling_point(self, calling_pnt: str):
        # TODO
        pass

    def _callback_function(self, state_arg):
        # get handles once
        if not self.got_ems_handles:
            # verify ems objects are ready for access, skip until
            if not self.api.exchange.api_data_fully_ready(state_arg):
                return
            self._set_ems_handles(state_arg)
            self.got_ems_handles = True

        # skip simulation warmup
        if self.api.exchange.warmup_flag(state_arg):
            return

        # update & append simulation data
        self._update_time()
        self._update_ems_vals()
        self._update_weather_vals()

        self.count += 1
        self.zone_ts += 1  # TODO make dependent on input file
        if self.zone_ts == 12:
            self.zone_ts = 1

    def _reset_state(self):
        self.api.state_manager.reset_state(self.state)

    def _delete_state(self):
        self.api.state_manager.delete_state(self.state)

    def _run_simulation(self, weather_file, calling_point):
        # set calling point with callback function
        getattr(self.api.runtime, calling_point)(self.state, self._callback_function)
        # run simulation
        self.api.runtime.run_energyplus(self.state,
                                        [
                                            '-w', weather_file,
                                            '-d', 'out',
                                            self.idf_file
                                        ]
                                        )














class EnergyPlusModel:
    # TODO figure out what idf and osm manipulation should be granted to user, or should they just do all this
    # or use openstudio package
    def __init__(self):
        pass


class BcaEnv(EmsPy):
    def __init__(self, ep_path, ep_idf_to_run, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc):
        super().__init__(ep_path, ep_idf_to_run, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc)

    def _get_observation(self):
        pass
        # return observation

    def _get_reward(self):
        pass
        # return reward

    def _take_action(self):
        pass

    def step_env(self):
        pass
        # return observation, reward, done, info

    def reset_sim(self, weather_file, calling_point):
        self._run_simulation(weather_file, calling_point)
        pass


class DataDashboard(BcaEnv):

    def __init__(self):
        pass

    def init_ddash(self):
        pass





    #####################################
# import emspy
# ep_path = ''  # path to EnergyPlus download in filesystem
# ep_file_path = ''  # path to .idf file for simulation
# ep_idf_to_run = ep_file_path + ''  #
# ep_weather_path = ep_path + '/WeatherData/.epw'
#
# # define EMS sensors and actuators to be used via 'Table of Contents'
# #vars_tc = [["attr_handle_name", "variable_type", "variable_key"],[...],...]
# # int_vars_tc = [["attr_handle_name", "variable_type", "variable_key"],[...],...]
# # meters_tc = [["attr_handle_name", "meter_name",[...],...]
# # actuators_tc = [["attr_handle_name", "component_type", "control_type", "actuator_key"],[...],...]
# # weather_tc = ["sun", "rain", "snow", "wind_dir", ...]
#
# ems = EmsPy(ep_path, ep_idf_to_run, vars_tc, int_vars_tc, meters_tc, actuators_tc)
# bca = ems.BcaEnv()
