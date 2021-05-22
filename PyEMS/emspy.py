import sys
import datetime


class EmsPy:
    """A meta-class wrapper to the EnergyPlus Python API to simplify/constrain usage for RL-algorithm purposes."""

    available_weather_metrics = ['sun_is_up', 'is_raining', 'is_snowing', 'albedo', 'beam_solar', 'diffuse_solar',
                                 'horizontal_ir', 'liquid_precipitation', 'outdoor_barometric_pressure',
                                 'outdoor_dew_point', 'outdoor_dry_bulb', 'outdoor_relative_humidity',
                                 'sky_temperature', 'wind_direction', 'wind_speed']

    def __init__(self, ep_path: str, ep_idf_to_run: str, timesteps: int, vars_tc: list, int_vars_tc: list,
                 meters_tc: list, actuators_tc: list, weather_tc: list):
        """
        Establish connection to EnergyPlusAPI and initializes desired EMS sensors, actuators, and weather data.

        This instantiation will implement the meta-class functionality - various handle and data list attributes will
        be created based on the user's input of desired EMS sensors, actuators, and weather data. Other functionality
        of the EnergyPlusAPI, not provided by this class, may also be accessed directly through the .pyapi pointer.

        :param ep_path: absolute path to EnergyPlus download directory in user's file system
        :param ep_idf_to_run: absolute/relative path to EnergyPlus building energy model to be simulated, .idf file
        :param timesteps: number of timesteps per hour set in EnergyPlus model .idf file
        :param vars_tc: list of desired output Variables, with each object provided as
        ['user_var_name', 'variable_name', 'variable_key'] within the list
        :param int_vars_tc: list of desired Internal Variables (static), with each object provided as
        ['user_var_name', 'variable_type', 'variable_key'] within the list
        :param meters_tc: list of desired Meters, with each object provided as
        ['user_var_name', 'meter_name'] within the list
        :param actuators_tc: list of desired EMS Actuators, with each object provided as
        ['user_var_name', 'component_type', 'control_type', 'actuator_key'] within the list
        :param weather_tc: list of desired weather types, pertaining to any available weather metrics defined below:
        ['sun_is_up', 'is_raining', 'is_snowing', 'albedo', 'beam_solar', 'diffuse_solar', 'horizontal_ir',
        'liquid_precipitation', 'outdoor_barometric_pressure', 'outdoor_dew_point', 'outdoor_dry_bulb',
        'outdoor_relative_humidity', 'sky_temperature', 'wind_direction', 'wind_speed']
        Any such weather metric can also be called for Today or Tomorrow for a given hour and timestep, if desired
        """
        self.ep_path = ep_path
        sys.path.insert(0, ep_path)  # set path to E+
        import pyenergyplus.api  # TODO add basic usability functions to
        from pyenergyplus.api import EnergyPlusAPI

        self.pyapi = pyenergyplus.api
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
        # timesteps and simulation iterations
        self.count = 0
        self.sys_ts = 0  # TODO nothing done with this yet
        self.zone_ts = 1  # fluctuate from one to # of timesteps per hour
        self.timestep_freq = timesteps
        self.timestep_period = 60/timesteps  # minute duration of each timestep of simulation

    def _init_ems_handles_and_data(self):
        """Creates and initializes the necessary instance attributes given by the user for the EMS sensors/actuators."""

        # set attribute handle names and data arrays given by user to None
        if self.vars_tc is not None:
            for var in self.vars_tc:
                setattr(self, 'handle_var_' + var[0], None)
                setattr(self, 'data_var_' + var[0], [])
        if self.int_vars_tc is not None:
            for int_var in self.int_vars_tc:
                setattr(self, 'handle_intvar_' + int_var[0], None)
                setattr(self, 'data_intvar_' + int_var[0], None)  # static val
        if self.meters_tc is not None:
            for meter in self.meters_tc:
                setattr(self, 'handle_meter_' + meter[0], None)
                setattr(self, 'data_meter_' + meter[0], [])
        if self.actuators_tc is not None:
            for actuator in self.actuators_tc:
                setattr(self, 'handle_actuator_' + actuator[0], None)
                setattr(self, 'data_actuator_' + actuator[0], [])

    def _init_weather_data(self):
        """Creates and initializes the necessary instance attributes given by the user for present weather metrics."""

        # verify provided weather ToC is accurate/acceptable
        for weather_metric in self.weather_tc:
            if weather_metric not in EmsPy.available_weather_metrics:
                raise Exception(f'{weather_metric} weather metric is misspelled or not provided by EnergyPlusAPI.')
        if self.weather_tc is not None:
            for weather_type in self.weather_tc:
                setattr(self, 'data_weather_' + weather_type, [])

    def _set_ems_handles(self):
        """Gets and reassigns the gathered sensor/actuators handles to their according _handle instance attribute."""

        if self.vars_tc is not None:
            for var in self.vars_tc:
                setattr(self, 'handle_var_' + var[0], self._get_handle('var', var))
        if self.int_vars_tc is not None:
            for int_var in self.int_vars_tc:
                setattr(self, 'handle_intvar_' + int_var[0], self._get_handle('int_var', int_var))
        if self.meters_tc is not None:
            for meter in self.meters_tc:
                setattr(self, 'handle_meter_' + meter[0], self._get_handle('meter', meter))
        if self.actuators_tc is not None:
            for actuator in self.actuators_tc:
                setattr(self, 'handle_actuator_' + actuator[0], self._get_handle('actuator', actuator))

    def _get_handle(self, ems_type: str, ems_obj: list):
        """
        Returns the EMS object handle to be used as its ID for calling functions on it in the running simulation.

        :param ems_type: The EMS object type (variable, internal variable, meter, actuator)
        :param ems_obj: The specific object details provided by the user to attain the handle
        """
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
                                                ' found. Please consult the .idf and/or your ToC for accuracy')
            else:
                return handle
        except IndexError:
            raise IndexError(str(ems_obj) + f': This {ems_type} object does not have all the required fields')

    def _update_time(self):
        """Updates all time-keeping and simulation timestep attributes of running simulation."""

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
        # manage time  tracking
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
        # manage timestep update
        if self.zone_ts > self.timestep_freq:
            self.zone_ts = 1
        else:
            self.zone_ts += 1


    def _update_ems_vals(self):
        """Updates and appends given sensor/actuator values from running simulation."""

        state = self.state
        datax = self.api.exchange
        if self.vars_tc is not None:
            for var in self.vars_tc:
                data_i = datax.get_variable_value(state, getattr(self, 'handle_var_' + var[0]))
                getattr(self, 'data_var_' + var[0]).append(data_i)
        if self.meters_tc is not None:
            for meter in self.meters_tc:
                data_i = datax.get_meter_value(state, getattr(self, 'handle_meter_' + meter[0]))
                getattr(self, 'data_meter_' + meter[0]).append(data_i)
        if self.actuators_tc is not None:
            for actuator in self.actuators_tc:
                data_i = datax.get_actuator_value(state, getattr(self, 'handle_actuator_' + actuator[0]))
                getattr(self, 'data_actuator_' + actuator[0]).append(data_i)
        # update static (internal) variables once
        if self.int_vars_tc is not None and not self.static_vars_gathered:
            for int_var in self.int_vars_tc:
                data_i = datax.get_internal_variable_value(state, getattr(self, 'handle_intvar_' + int_var[0]))
                getattr(self, 'data_intvar_' + int_var[0]).append(data_i)
                self.static_vars_gathered = True

    def _update_weather_vals(self):
        """Updates and appends given weather metric values from running simulation."""

        if self.weather_tc is not None:
            for weather_type in self.weather_tc:
                data_i = self._get_weather('today', weather_type, self.hours[-1], self.zone_ts)
                getattr(self, 'data_weather_' + weather_type).append(data_i)

    def _get_weather(self, when: str, weather_type: str, hour: int, zone_ts: int):
        """


        :param when:
        :param weather_type:
        :param hour:
        :param zone_ts:
        :return:
        """
        if weather_type is not 'sun_is_up':
            return getattr(self.api.exchange, when + '_weather_' + weather_type + '_at_time')(self.state, hour, zone_ts)
        elif weather_type is 'sun_is_up':
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
            self._set_ems_handles()
            self.got_ems_handles = True

        # skip simulation warmup
        if self.api.exchange.warmup_flag(state_arg):
            return

        # update & append simulation data
        self._update_time()  # note timing update is first
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






class BcaEnv(EmsPy):
    def __init__(self, ep_path, ep_idf_to_run, timesteps, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc):
        super().__init__(ep_path, ep_idf_to_run, timesteps, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc)

        self.reward = 0
        self.cumulative_reward = 0

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

class EnergyPlusModel:
    # TODO figure out what idf and osm manipulation should be granted to user, or should they just do all this
    # or use openstudio package
    def __init__(self):
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
