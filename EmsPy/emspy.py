"""
This program was constructed with the inspiration from the demo work of Julien Marrec
https://github.com/jmarrec/OpenStudio_to_EnergyPlusAPI/blob/main/OpenStudio_to_EnergyPlusAPI.ipynb

EnergyPlus Python API 0.2 documentation https://eplus.readthedocs.io/en/stable/
EnergyPlus documentation (EMS Application Guide) https://energyplus.net/documentation
OpenStudio SDK documentation http://nrel.github.io/OpenStudio-user-documentation/
Unmet Hours help forum https://unmethours.com/questions/
"""

import sys
import datetime
import pandas as pd


class EmsPy:
    """A meta-class wrapper to the EnergyPlus Python API to simplify/constrain usage for RL-algorithm purposes."""

    available_weather_metrics = ['sun_is_up', 'is_raining', 'is_snowing', 'albedo', 'beam_solar', 'diffuse_solar',
                                 'horizontal_ir', 'liquid_precipitation', 'outdoor_barometric_pressure',
                                 'outdoor_dew_point', 'outdoor_dry_bulb', 'outdoor_relative_humidity',
                                 'sky_temperature', 'wind_direction', 'wind_speed']

    available_calling_points = ['callback_after_component_get_input',
                                'callback_after_new_environment_warmup_complete',
                                'callback_after_predictor_after_hvac_managers',
                                'callback_after_predictor_before_hvac_managers',
                                'callback_begin_new_environment',
                                'callback_begin_system_timestep_before_predictor',
                                'callback_begin_zone_timestep_after_init_heat_balance',
                                'callback_begin_zone_timestep_before_set_current_weather',
                                'callback_end_system_sizing',
                                'callback_end_system_after_hvac_reporting',
                                'callback_end_system_timestep_before_hvac_reporting'
                                'callback_end_zone_sizing',
                                'callback_end_zone_timestep_after_zone_reporting',
                                'callback_end_zone_timestep_before_zone_reporting',
                                'callback_inside_system_iteration_loop']  # TODO verify correctness

    def __init__(self, ep_path: str, ep_idf_to_run: str, timesteps: int,
                 tc_var: dict, tc_intvar: dict, tc_meter: dict, tc_actuator: dict, tc_weather: dict):
        """
        Establish connection to EnergyPlusAPI and initializes desired EMS sensors, actuators, and weather data.

        This instantiation will implement the meta-class functionality - various handle and data list attributes will
        be created based on the user's input of desired EMS sensors, actuators, and weather data. Understanding what
        sensors and actuators are available, and how they are labeled, requires a reasonably well understanding of your
        EnergyPlus model and it's .idf file, as well as the .edd and .rdd output files. Other functionality of the
        EnergyPlusAPI, not provided by this simplified class, may also be accessed directly through the .pyapi pointer.

        :param ep_path: absolute path to EnergyPlus download directory in user's file system
        :param ep_idf_to_run: absolute/relative path to EnergyPlus building energy model to be simulated, .idf file
        :param timesteps: number of timesteps per hour set in EnergyPlus model .idf file
        :param tc_var: dict of desired output Variables, with each EMS object provided as
        'user_var_name': ['variable_name', 'variable_key'] within the dict
        :param tc_intvar: list of desired Internal Variables (static), with each object provided as
        'user_var_name': ['variable_type', 'variable_key'] within the dict
        :param tc_meter: list of desired Meters, with each object provided as
        'user_var_name': 'meter_name' within the dict
        :param tc_actuator: list of desired EMS Actuators, with each object provided as
        'user_var_name': ['component_type', 'control_type', 'actuator_key'] within the dict

        :param tc_weather: list of desired weather types, with each object provided as
        'user_var_name': 'weather_metric' within the dict.
        The available weather metrics are identified below:
        ['sun_is_up', 'is_raining', 'is_snowing', 'albedo', 'beam_solar', 'diffuse_solar', 'horizontal_ir',
        'liquid_precipitation', 'outdoor_barometric_pressure', 'outdoor_dew_point', 'outdoor_dry_bulb',
        'outdoor_relative_humidity', 'sky_temperature', 'wind_direction', 'wind_speed']
        Any such weather metric can also be called for Today or Tomorrow for a given hour and timestep, if desired
        """

        self.ep_path = ep_path
        sys.path.insert(0, ep_path)  # set path to E+
        import pyenergyplus.api
        from pyenergyplus.api import EnergyPlusAPI

        self.pyapi = pyenergyplus.api
        self.api = EnergyPlusAPI()  # instantiation of Python EMS API

        # instance important below
        self.state = self._new_state()  # TODO determine if multiple state instances should be allowed (new meta attr.)
        self.idf_file = ep_idf_to_run  # E+ idf file to simulation

        # Table of Contents for EMS sensor and actuators
        self.tc_var = tc_var
        self.tc_intvar = tc_intvar
        self.tc_meter = tc_meter
        self.tc_actuator = tc_actuator

        # Table of Content for present weather data
        self.tc_weather = tc_weather

        # dataframes
        self.df_count = 0
        self.df_custom_dict = {}  # key: dict_name, val: ([ems_list], 'calling_point', update freq)
        self.df_var = None
        self.df_intvar = None
        self.df_meter = None
        self.df_actuator = None
        self.weather = None

        # summary dicts and lists
        self.times_master_list = ['actual_date_time', 'actual_times', 'current_times', 'years', 'months', 'days',
                                  'hours', 'minutes', 'time_x', 'timesteps', 'timesteps_total'
                                  'callbacks']  # list of available time data user can call
        self.ems_names_master_list = self.times_master_list  # keeps track of all user-defined and default EMS var names
        self.ems_type_dict = {}  # keep track of EMS metric names and associated EMS type, quick lookup
        self.ems_num_dict = {} # keep track of EMS variable categories and num of vars for each
        self.ems_current_data_dict = {}  # collection of all ems metrics (keys) and their current values (val)
        self.calling_point_actuation_dict = {}  # links cp to actuation fxn & its needed args

        # create attributes of sensor and actuator .idf handles and data arrays
        self._init_ems_handles_and_data()  # creates ems_handle = int & ems_data = [] attributes, and variable counts
        self.got_ems_handles = False
        self.static_vars_gathered = False  # static (internal) variables, gather once

        # create attributes for weather
        self._init_weather_data()  # creates weather_data = [] attribute, useful for present/prior weather data tracking

        # timing data
        self.actual_date_times = []
        self.actual_times = []
        self.current_times = []
        self.years = []
        self.months = []
        self.days = []
        self.hours = []
        self.minutes = []
        self.time_x = []
        # timestep, callback data
        self.timesteps = []
        self.timesteps_total = []
        self.callbacks = []

        # timesteps and simulation iterations
        self.timestep_total_count = 0  # cnt for entire simulation # TODO how to enforce only once per ts
        self.callback_count = 0
        self.timestep_zone_current = 1  # fluctuate from 1 to # of timesteps/hour # TODO how to enforce only once per ts
        self.timestep = self._init_timestep(timesteps)  # sim timesteps per hour # TODO enforce via OPENSTUDIO SDK ???
        self.timestep_period = 60 // timesteps  # minute duration of each timestep of simulation
        self.simulation_ran = False

    def _init_ems_handles_and_data(self):
        """
        Creates and initializes the necessary instance attributes given by the user for the EMS sensors/actuators.

        This will initialize data list and EMS handle attributes to the proper Null value for each EMS variable,
        internal variable, meter, and actuator as outlined by the user in their respective Table of Contents variable.
        All of these attributes need to be initialized for later use, using the 'variable name' of the object in the
        first element of each ToC element. Then 'handle_' and 'data_' will be added to the given name to further specify
        the created attribute.
        This will also update the EMS dictionary which tracks which EMS variable types are in use and how many for each
        category. This dictionary attribute is used elsewhere for quick data fetching.
        """
        # set attribute handle names and data arrays given by user to None
        ems_types = ['var', 'intvar', 'meter', 'actuator']
        for ems_type in ems_types:
            ems_tc = getattr(self, 'tc_' + ems_type)
            if ems_tc is not None:
                for ems_name in ems_tc:
                    setattr(self, 'handle_' + ems_type + '_' + ems_name, None)
                    setattr(self, 'data_' + ems_type + '_' + ems_name, [])
                    self.ems_type_dict[ems_name] = ems_type
                    self.ems_names_master_list.append(ems_name)  # all ems metrics collected
                self.ems_num_dict[ems_type] = len(ems_tc)  # num of metrics per ems category
                self.df_count += 1

        # handle available timing data dict type
        for t in self.times_master_list:
            self.ems_type_dict[t] = 'time'

    def _init_weather_data(self):
        """Creates and initializes the necessary instance attributes given by the user for present weather metrics."""

        if self.tc_weather is not None:
            # verify provided weather ToC is accurate/acceptable
            for weather_name, weather_metric in self.tc_weather.items():
                if weather_metric not in EmsPy.available_weather_metrics:
                    raise Exception(f'{weather_metric} weather metric is misspelled or not provided by EnergyPlusAPI.')
                setattr(self, 'data_weather_' + weather_name, [])
                self.ems_names_master_list.append(weather_name)
                self.ems_type_dict[weather_name] = 'weather'
            self.ems_num_dict['weather'] = len(self.tc_weather)
            self.df_count += 1

    def _init_timestep(self, timestep: int) -> int:
        """This function is used to verify timestep input correctness & report any details/changes."""

        # TODO upgrade functionality
        available_timesteps = [1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60]

        if timestep not in available_timesteps:
            raise ValueError(f'Your choice of number of timesteps per hour, {timestep}, must be evenly divisible into'
                             f' 60 mins: {available_timesteps}')
        else:
            print(f'Your simulation timestep period is {60 // timestep} minutes')
            return timestep

    def _set_ems_handles(self):
        """Gets and reassigns the gathered sensor/actuators handles to their according _handle instance attribute."""

        ems_types = ['var', 'intvar', 'meter', 'actuator']
        for ems_type in ems_types:
            ems_tc = getattr(self, 'tc_' + ems_type)
            if ems_tc is not None:
                for name in ems_tc:
                    handle_inputs = ems_tc[name]
                    setattr(self, 'handle_' + ems_type + '_' + name, self._get_handle(ems_type, handle_inputs))

    def _get_handle(self, ems_type: str, ems_obj_details):
        """
        Returns the EMS object handle to be used as its ID for calling functions on it in the running simulation.

        :param ems_type: The EMS object type (variable, internal variable, meter, actuator)
        :param ems_obj_details: The specific object details provided by the user to attain the handle
        """
        state = self.state
        datax = self.api.exchange
        try:
            handle = ""
            if ems_type is 'var':
                handle = datax.get_variable_handle(state,
                                                   ems_obj_details[0],  # var name
                                                   ems_obj_details[1])  # var key
            elif ems_type is 'intvar':
                handle = datax.get_internal_variable_handle(state,
                                                            ems_obj_details[0],  # int var name
                                                            ems_obj_details[1])  # int var key
            elif ems_type is 'meter':
                handle = datax.get_meter_handle(state,
                                                ems_obj_details)  # meter name
            elif ems_type is "actuator":
                handle = datax.get_actuator_handle(state,
                                                   ems_obj_details[0],  # component type
                                                   ems_obj_details[1],  # control type
                                                   ems_obj_details[2])  # actuator key
            # catch error handling by EMS E+
            if handle == -1:
                raise Exception(str(ems_obj_details) + ': The EMS sensor/actuator handle could not be'
                                                       ' found. Please consult the .idf and/or your ToC for accuracy')
            else:
                return handle
        except IndexError:
            raise IndexError(str(ems_obj_details) + f': This {ems_type} object does not have all the required fields '
                                                    f' get the EMS handle')

    def _update_time(self):
        """Updates all time-keeping and simulation timestep attributes of running simulation."""

        state = self.state
        api = self.api
        # gather data
        # TODO add current timestep ems variable by default
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
        # time keeping dataframe management
        dt = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute)
        dt += timedelta
        self.time_x.append(dt)
        self.ems_current_data_dict['Datetime'] = dt

        # manage timestep update
        # TODO make dependent on input file OR handle mistake where user enters incorrect ts
        self.timestep_total_count += 1  # TODO should this be done once per timestep or callback
        self.timesteps_total = self.timestep_total_count
        # update current zone timestep
        if self.timestep_zone_current >= self.timestep:
            self.timestep_zone_current = 1
        else:
            self.timestep_zone_current += 1
        # update data
        self.timesteps.append(self.timestep_zone_current)

    def _update_ems_vals(self, ems_metrics_list: list):
        """Fetches and updates given sensor/actuator/weather values to data lists/dicts from running simulation."""

        # specific data exchange API function calls
        datax = self.api.exchange
        ems_datax_func = {'var': datax.get_variable_value,
                          'intvar': datax.get_internal_variable_value,
                          'meter': datax.get_meter_value,
                          'actuator': datax.get_actuator_value}

        for ems_name in ems_metrics_list:
            ems_type = self.ems_type_dict[ems_name]
            if ems_type is 'weather':
                self._update_weather_vals(ems_name)
            else:
                # get data
                data_i = ems_datax_func[ems_type](self.state, getattr(self, 'handle_' + ems_type + '_' + ems_name))
                # store data in attributes
                getattr(self, 'data_' + ems_type + '_' + ems_name).append(data_i)
                self.ems_current_data_dict[ems_name] = data_i

    def _update_weather_vals(self, weather_name):
        """Updates and appends given weather metric values to data lists/dicts from running simulation."""

        data_i = self._get_weather([weather_name], 'today', self.hours[-1], self.timestep_zone_current)
        getattr(self, 'data_weather_' + weather_name).append(data_i)
        self.ems_current_data_dict[weather_name] = data_i

    def _get_weather(self, weather_metrics: list, when: str,  hour: int, zone_ts: int) -> list:
        """
        Gets desired weather metric data for a given hour and zone timestep, either for today or tomorrow in simulation.

        :param weather_metrics: the weather metrics to call from E+ API, only specific fields from ToC are granted
        :param when: the day in question, 'today' or 'tomorrow', relative to current simulation time
        :param hour: the hour of the day to call the weather value
        :param zone_ts: the zone timestep of the given hour to call the weather value
        :return: list of updated weather data in order of weather_metrics input list
        """
        # input error handling
        if not (when is 'today' or when is 'tomorrow'):
            raise Exception('Weather data must either be called from sometime today or tomorrow relative to current'
                            'simulation timestep.')
        if hour > 24 or hour < 0:
            raise Exception('The hour of the day cannot exceed 24 or be less than 0')
        if zone_ts > self.timestep:
            raise Exception(f'The desired timestep, {zone_ts} cannot exceed the subhourly simulation timestep set for'
                            f' the model, {self.timestep}.')

        # fetch weather
        weather_data = []
        for weather_name in weather_metrics:
            # input error handling
            if weather_name not in self.tc_weather:
                raise Exception(f'Invalid weather metric ({weather_name}) given. Please see your weather ToC for'
                                ' available weather metrics.')

            weather_metric = self.tc_weather[weather_name]
            # sun weather type is unique to rest, doesn't follow consistent naming system
            if weather_metric is not 'sun_is_up':
                weather_data.append(getattr(self.api.exchange, when + '_weather_' + weather_metric + '_at_time')\
                                    (self.state, hour, zone_ts))
            elif weather_metric is 'sun_is_up':
                weather_data.append(self.api.exchange.sun_is_up(self.state))
        return weather_data

    def _actuate(self, actuator_handle: str, actuator_val):
        """ Sets value of a specific actuator in running simulator, or relinquishes control back to EnergyPlus."""

        # use None to relinquish control
        # TODO should I handle out-of-range actuator values??? (can this be managed with auto internal var lookup?)
        if actuator_val is None:
            self.api.exchange.reset_actuator(self.state, actuator_handle)  # return actuator control to EnergyPlus
        else:
            self.api.exchange.set_actuator_value(self.state, actuator_handle, actuator_val)

    def _actuate_from_list(self, calling_point: str, actuator_setpoint_dict: dict):
        """
        This iterates through list of actuator name and value setpoint pairs to be set in simulation.

        CAUTION: Actuation functions written by user must return an actuator_name(key)-value pair dictionary

        :param calling_point: only used for error output message to user
        :param actuator_setpoint_dict: dict of actuator name keys (str) & associated setpoint val
        """
        if actuator_setpoint_dict is not None:  # in case some 'actuation functions' does not actually act
            for actuator_name, actuator_setpoint in actuator_setpoint_dict.items():
                if actuator_name not in self.tc_actuator:
                    raise Exception(f'Either this actuator {actuator_name} is not tracked, or misspelled.'
                                    f'Check your Actuator ToC.')
                actuator_handle = getattr(self, 'handle_actuator_' + actuator_name)
                self._actuate(actuator_handle, actuator_setpoint)
                self.ems_current_data_dict[actuator_name] = actuator_setpoint
        else:
            # print(f'WARNING: No actuators/values defined for actuation function at calling point {calling_point},'
            #       f' timestep {self.timestep_zone_current}')
            pass

    def _enclosing_callback(self, calling_point: str, observation_fxn, actuation_fxn,
                            update_state: bool = False,
                            update_state_freq: int = 1,
                            update_act_freq: int = 1):
        """
        Decorates the main callback function to set the user-defined calling function and set timing and data params.

        # TODO specify Warning documentation and find a way to check if only one data/timing update is done per timestep
        :param calling_point: the calling point at which the callback function will be called during simulation runtime
        :param observation_fxn: the user defined observation function to be called at runtime calling point and desired
        timestep frequency
        :param actuation_fxn: the user defined actuation function to be called at runtime calling point and desired
        timestep frequency
        :param update_state: whether EMS and time/timestep should be updated. This should only be done ONCE a timestep
        :param update_state_freq: the number of zone timesteps per updating the simulation state
        :param update_act_freq: the number of zone timesteps per updating the actuators from the actuation function
        """

        def _callback_function(state_arg):
            """
            The main callback passed to the running EnergyPlus simulation, this commands the interaction.

            :param state_arg: NOT USED by this API - passed to and used internally by EnergyPlus simulation
            """
            # get ems handles once
            if not self.got_ems_handles:
                # verify ems objects are ready for access, skip until
                if not self.api.exchange.api_data_fully_ready(state_arg):
                    return
                self._set_ems_handles()
                self.got_ems_handles = True

            # skip if simulation in warmup
            if self.api.exchange.warmup_flag(state_arg):
                return

            # TODO verify freq robustness
            if update_state and self.timestep_zone_current % update_state_freq == 0:
                # update & append simulation data
                self._update_time()  # note timing update is first
                self._update_ems_vals(self.ems_names_master_list)  # update sensor/actuator/weather/etc. vals
                # run user-defined agent state update function
                if observation_fxn is not None:
                    observation_fxn()

            # TODO verify freq robustness
            if actuation_fxn is not None and self.timestep_zone_current % update_act_freq == 0:
                self._actuate_from_list(calling_point, actuation_fxn())

            # update custom dataframes
            self._update_custom_dataframe_dicts(calling_point)
            # update callback count data
            self.callback_count += 1
            self.callbacks.append(self.callback_count)

        return _callback_function

    def _init_calling_points_and_callback_functions(self):
        """This iterates through the Calling Point Dict{} to set runtime calling points with actuation functions."""

        if not self.calling_point_actuation_dict:
            print('Warning: No calling points or callback function initiated. Will just run simulation!')
            return  # TODO verify intentions - no callbacks, just run sim from python

        for calling_key in self.calling_point_actuation_dict:
            # check if user-specified calling point is correct and available
            if calling_key not in self.available_calling_points:
                raise Exception(f'This calling point \'{calling_key}\' is not a valid calling point. Please see the'
                                f' Python API documentation and available calling point list'
                                f'EmsPy.available_calling_points class attribute.')
            else:
                # unpack observation & actuation fxns and callback fxn arguments
                unpack = self.calling_point_actuation_dict[calling_key]
                observation_fxn, actuation_fxn, update_state, update_state_freq, update_act_freq = unpack
                # establish calling points at runtime and create/pass its custom callback function
                getattr(self.api.runtime, calling_key)(self.state, self._enclosing_callback(calling_key,
                                                                                            observation_fxn,
                                                                                            actuation_fxn,
                                                                                            update_state,
                                                                                            update_state_freq,
                                                                                            update_act_freq))

    def init_custom_dataframe_dict(self, df_name: str, calling_point: str, update_freq: int, ems_metrics: list):
        """
        Used to initialize EMS metric pandas dataframe attributes.

        :param df_name: user-defined df variable name
        :param calling_point: the calling point at which the df should be updated
        :param update_freq: how often data will be posted, it will be posted every X timesteps
        :param ems_metrics: list of EMS metric var names to store their data points in df
        """

        if calling_point not in self.calling_point_actuation_dict:
            raise Exception(f'Invalid Calling Point name \'{calling_point}\'. Please see your declared available '
                            f'calling points {self.calling_point_actuation_dict.keys()}.')
        # metric names must align with the EMS metric names assigned in var, intvar, meters, actuators, weather ToC's
        ems_custom_dict = {'Datetime': []}
        for metric in ems_metrics:
            ems_type = ''
            if metric not in self.ems_names_master_list:
                raise Exception('Incorrect EMS metric names were entered for custom dataframes.')
            # create dict to collect data for pandas dataframe
            ems_custom_dict[metric] = []
        # add to dataframe dict
        self.df_custom_dict[df_name] = (ems_custom_dict, calling_point, update_freq)
        self.df_count += 1

    def _update_custom_dataframe_dicts(self, calling_point):
        """Updates data based on desired calling point, frequency, and specific ems vars."""

        if not self.df_custom_dict:
            return  # no custom dicts created
        # iterate through and update all default and user-defined dataframes
        for df_name in self.df_custom_dict:
            ems_dict, cp, update_freq = self.df_custom_dict[df_name]  # unpack value
            # TODO verify if % mod is robust enough for interval collection
            if cp is calling_point and self.timestep_total_count % update_freq == 0:
                for ems_metric in ems_dict:
                    # get most recent data point
                    if ems_metric is 'Datetime':
                        data_i = self.time_x[-1]
                    else:
                        ems_type = self.get_ems_type(ems_metric)
                        data_list_name = 'data_' + ems_type + '_' + ems_metric
                        data_i = getattr(self, data_list_name)[-1]
                        # append to dict list
                    self.df_custom_dict[df_name][0][ems_metric].append(data_i)

    def _create_custom_dataframes(self):
        """Creates custom dataframes for specifically tracked ems data list, for each ems category."""

        if not self.df_custom_dict:
            return  # no ems dicts created, very unlikely
        for df_name in self.df_custom_dict:
            ems_dict, _, _ = self.df_custom_dict[df_name]
            setattr(self, df_name, pd.DataFrame.from_dict(ems_dict))

    def _create_default_dataframes(self):
        """Creates default dataframes for each EMS data list, for each ems category."""

        if not self.ems_num_dict:
            return  # no ems dicts created, very unlikely
        ems_dict = {'Datetime': self.time_x}
        for ems_type in self.ems_num_dict:
            for ems_name in getattr(self, 'tc_' + ems_type):
                ems_data_list_name = 'data_' + ems_type + '_' + ems_name
                ems_dict[ems_name] = getattr(self, ems_data_list_name)
            # create default df
            df_name = 'df_' + ems_type
            setattr(self, df_name, pd.DataFrame.from_dict(ems_dict))

    def get_ems_type(self, ems_metric: str):
        """ Returns EMS (var, intvar, meter, actuator, weather) or time type string for a given ems metric variable."""
        return self.ems_type_dict[ems_metric]  # used to create attribute var names 'data_' + type

    def _user_input_check(self):
        # TODO create function that checks if all user-input attributes has been specified and add help directions
        if not self.calling_point_actuation_dict:
            print('WARNING: No calling points or actuation/observation functions were initialized.')
        pass

    def _new_state(self):
        """Creates & returns a new state instance that's required to pass into EnergyPlus Runtime API function calls."""
        return self.api.state_manager.new_state()

    def reset_state(self):
        """Resets the state instance of a simulation per EnergyPlus State API documentation."""
        self.api.state_manager.reset_state(self.state)

    def delete_state(self):
        """Deletes the existing state instance."""
        self.api.state_manager.delete_state(self.state)

    def run_simulation(self, weather_file: str):
        """This runs the EnergyPlus simulation and RL experiment."""

        # check valid input by user
        self._user_input_check()

        self._init_calling_points_and_callback_functions()

        # RUN SIMULATION
        print('* * * Running E+ Simulation * * *')
        self.api.runtime.run_energyplus(self.state, ['-w', weather_file, '-d', 'out', self.idf_file])   # cmd line args
        self.simulation_ran = True
        # create default and custom ems pandas df's after simulation complete
        self._create_default_dataframes()
        self._create_custom_dataframes()


class BcaEnv(EmsPy):
    """
    This class represents the Building Control Agent (BCA) and Environment for RL. It represents a higher layer
    of abstraction to its parent class, EmsPy, encapsulating more complex features and acting as the UI.
    Users should be able to perform all necessary interactions for control algorithm experimentation mostly or
    completely through this class.
    """

    # Building Control Agent (BCA) & Environment
    def __init__(self, ep_path: str, ep_idf_to_run: str, timesteps: int,
                 tc_vars: dict, tc_intvars: dict, tc_meters: dict, tc_actuator: dict, tc_weather: dict):
        """See EmsPy.__init__() documentation."""
        # follow same init procedure as parent class EmsPy
        super().__init__(ep_path, ep_idf_to_run, timesteps, tc_vars, tc_intvars, tc_meters, tc_actuator, tc_weather)

    def set_calling_point_and_callback_function(self, calling_point: str,
                                                observation_fxn,
                                                actuation_fxn,
                                                update_state: bool,
                                                update_state_freq: int = 1,
                                                update_act_freq: int = 1):
        """
        Modify dict for runtime calling points and custom callback function specification with defined arguments.

        This will be used to created user-defined callback functions, including an  optional observation function,
        actuation function, state update condition, and state update and action update frequencies. This allows the user
        to create the conventional RL agent interaction -> get state -> take action, each with desired timestep
        frequencies of implementation.

        :param calling_point: the calling point at which the callback function will be called during simulation runtime
        :param observation_fxn: the user defined observation function to be called at runtime calling point and desired
        timestep frequency, to be used to gather state data for agent before taking actions.
        :param actuation_fxn: the user defined actuation function to be called at runtime calling point and desired
        timestep frequency, function must return dict of actuator names (key) and associated setpoint (value)
        :param update_state: whether EMS and time/timestep should be updated. This should only be done once a timestep
        :param update_state_freq: the number of zone timesteps per updating the simulation state
        :param update_act_freq: the number of zone timesteps per updating the actuators from the actuation function
        """

        # TODO specify Warning documentation and find a way to check if only one data/timing update is done per timestep
        if update_act_freq > update_state_freq:
            print(f'WARNING: it is unusual to have your action update more frequent than your state update')
        if calling_point in self.calling_point_actuation_dict:
            raise Exception(
                f'You have overrided the calling point {calling_point}. Please keep calling points unique.')
        else:
            self.calling_point_actuation_dict[calling_point] = [observation_fxn, actuation_fxn, update_state,
                                                                update_state_freq, update_act_freq]

    def get_ems_data(self, ems_metric_list: list, time_rev_index: list = 0) -> list:
        """
        This takes desired EMS metric(s) (or type) & returns the entire current data set(s) OR at specific time indices.

        This function should be used to collect user-defined state space OR time information at each timestep. 1 to all
        EMS metrics and timing can be called, or just EMS category (var, intvar, meter, actuator, weather) and one data
        point to the entire data set can be returned. It is likely that the user will want the most recent data point
        only and should implement a time_index of [0].

        If calling default timing data, see EmsPy.times_master_list for available default timing data.

        :param ems_metric_list: list of strings (or single element) of any available EMS/timing metric(s) to be called,
        or ONLY ONE entire EMS category (var, intvar, meter, actuator, weather)
        :param time_rev_index: list (or single value) of timestep indexes, applied to all EMS/timing metrics starting
        from index 0 as most recent available data point. An empty list [] will return the entire current data list for
        each metric.
        :return return_data_list: nested list of data for each EMS metric at each time index specified, or entire list
        """
        # handle single val inputs -> convert to list for rest of function
        single_val = False

        if type(ems_metric_list) is not list:  # assuming single metric
            ems_metric_list = [ems_metric_list]
        if type(time_rev_index) is not list:  # assuming single val
            time_rev_index = [time_rev_index]
            single_val = True

        return_data_list = []

        # check if only EMS category called
        if ems_metric_list[0] in self.ems_num_dict and len(ems_metric_list) == 1:
            ems_metric_list = list(getattr(self, 'tc_' + ems_metric_list[0]).keys())  # reassign entire EMS type list
        else:
            # verify valid input
            for ems_metric in ems_metric_list:
                # TODO only input error check once as this gets called every callback
                if ems_metric in self.ems_num_dict:
                    raise Exception(f'EMS categories can only be called by themselves, please only call one at a time.')
                elif ems_metric not in self.ems_names_master_list and ems_metric not in self.times_master_list:
                    raise Exception(f'The EMS/timing metric \'{ems_metric}\' is not valid. Please see your EMS ToCs or '
                                    'EmsPy.ems_master_list & EmsPy.times_master_list for available EMS & timing '
                                    'metrics')

                ems_type = self.get_ems_type(ems_metric)
                # no time index specified, return full data list
                if not time_rev_index:
                    return_data_list.append(getattr(self, 'data_' + ems_type + '_' + ems_metric))
                else:
                    if self.timestep_total_count > max(time_rev_index):
                        return_data_indexed = []
                        for time in time_rev_index:
                            if ems_type is not 'time':
                                ems_name = 'data_' + ems_type + '_' + ems_metric
                            else:
                                ems_name = ems_metric
                            data_indexed = getattr(self, ems_name)[-1 - time]
                            if single_val:
                                # so that a single-element nested list is not returned
                                return_data_indexed = data_indexed  # no list of vals collected
                            else:
                                return_data_indexed.append(data_indexed)
                        return_data_list.append(return_data_indexed)

                    else:
                        print("NOTE: Not enough simulation timesteps have elapsed to gather all time indexes"
                              " - Empty list [] returned.")
                        return []

        return return_data_list

    def get_weather_forecast(self, weather_metrics: list, when: str, hour: int, zone_ts: int):
        """
        Fetches given weather metric from today/tomorrow for a given hour of the day and timestep within that hour.

        :param weather_metrics: list of desired weather metric(s) (1 to all) from weather ToC dict
        :param when: 'today' or 'tomorrow' relative to current timestep
        :param hour: hour of day
        :param zone_ts: timestep of hour
        """

        return self._get_weather(weather_metrics, when, hour, zone_ts)

    def update_ems_data(self, ems_metric_list: list, return_data: bool) -> list:
        """
        This takes desired EMS metric(s) (or type) to fetch and return the value, but does not update the attributes.

        This optional function can be used to collect specific EMS at each timestep for a given calling point. One to
        all EMS metrics can be called, or just EMS category (var, intvar, meter, actuator, weather) and have the data
        point update returned. This is only needed if the user wants to update specific EMS metrics at a unique calling
        point separate from ALL EMS metrics during default state update.

        This also works for default timing data.

        :param ems_metric_list: list of any available EMS metric(s) to be called, or ONLY ONE entire EMS category
        (var, intvar, meter, actuator, weather) in a list
        :param return_data: Whether or not to return an order list of the data points fetched
        :return return_data_list: list of fetched data for each EMS metric at each time index specified or []
        """

        full_ems_category = False
        # if only EMS category called
        if ems_metric_list[0] in self.ems_num_dict and len(ems_metric_list) == 1:
            ems_metric_list = list(getattr(self, 'tc_' + ems_metric_list[0]).keys())
            full_ems_category = True
        for ems_metric in ems_metric_list:
            # TODO only input error check once as this gets called every callback
            if not full_ems_category:
                if ems_metric in self.ems_num_dict:
                    raise Exception(f'EMS categories can only be called by themselves, please only call one at a time.')
                elif ems_metric not in self.ems_names_master_list:
                    raise Exception(f'The EMS metric {ems_metric} is not valid. Please see your ToCs or '
                                    f'.ems_master_list for available metrics.')

        self._update_ems_vals(ems_metric_list)
        if return_data:
            return self.get_ems_data(ems_metric_list)
        else:
            return []

    def get_df(self, df_name: list):
        """
        Returns selected EMS-type default dataframe based on user's entered ToC(s) or custom DF.

        :param df_name: default EMS metric type (var, intvar, meter, actuator, weather) OR custom df name
        :return: pandas dataframe
        """
        if not self.simulation_ran:
               raise Exception('Simulation must be run first to fetch data.')

        if type(df_name) is not list:
            df_name = [df_name]
        return_df = []
        for df in df_name:
            if df in self.ems_num_dict:
                return_df.append(getattr(self, 'df_' + df))
            elif df in self.df_custom_dict:
                return_df.append(getattr(self, df))
            else:
                raise ValueError('Either dataframe custom name or default type is not valid or was not collected during'
                                 'simulation')
        return return_df

    def run_env(self, weather_file: str):
        self.run_simulation(weather_file)
        pass


class DataDashboard:
    # TODO
    def __init__(self):
        pass


class EnergyPlusModelModifier:
    # TODO figure out what idf and osm manipulation should be granted to user, or should they just do all this
    # or use openstudio package
    def __init__(self):
        pass
