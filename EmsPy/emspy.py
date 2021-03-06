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
                                'callback_end_zone_sizing',
                                'callback_end_system_sizing',
                                'callback_begin_new_environment',
                                'callback_after_new_environment_warmup_complete',
                                'callback_begin_zone_timestep_before_init_heat_balance',
                                'callback_begin_zone_timestep_after_init_heat_balance',
                                'callback_after_predictor_after_hvac_managers',
                                'callback_after_predictor_before_hvac_managers',
                                'callback_begin_system_timestep_before_predictor',
                                'callback_begin_zone_timestep_before_set_current_weather',
                                'callback_end_system_timestep_after_hvac_reporting',
                                'callback_end_system_timestep_before_hvac_reporting',
                                'callback_end_zone_timestep_after_zone_reporting',
                                'callback_end_zone_timestep_before_zone_reporting',
                                'callback_inside_system_iteration_loop']

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
        self.state = self._new_state()
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
        self.df_weather = None
        self.custom_dataframes_initialized = False

        # summary dicts and lists
        self.times_master_list = ['actual_date_time', 'actual_times', 'current_times', 'years', 'months', 'days',
                                  'hours', 'minutes', 'time_x', 'timesteps_zone', 'timesteps_zone_num'
                                  'callbacks']  # list of available time data user can call
        self.ems_names_master_list = self.times_master_list[:]  # keeps track of all user & default EMS var names
        self.ems_type_dict = {}  # keep track of EMS metric names and associated EMS type, quick lookup
        self.ems_num_dict = {}  # keep track of EMS variable categories and num of vars for each
        self.ems_current_data_dict = {}  # collection of all ems metrics (keys) and their current values (val)
        self.calling_point_actuation_dict = {}  # links cp to actuation fxn & its needed args

        # create attributes of sensor and actuator .idf handles and data arrays
        self._init_ems_handles_and_data()  # creates ems_handle = int & ems_data = [] attributes, and variable counts
        self.got_ems_handles = False
        self.static_vars_obtained = False  # static (internal) variables, gather once
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
        # timestep
        self.timestep_input = timesteps
        self.timesteps_zone_num = []
        self.timestep_zone_num_current = 0  # fluctuate from 1 to # of timesteps/hour
        self.timestep_total_count = 0  # cnt for entire simulation
        self.timestep_per_hour = None  # sim timesteps per hour, initialized later
        self.timestep_period = None  # minute duration of each timestep of simulation, initialized later
        self.timestep_params_initialized = False

        # callback data
        self.callback_calling_points = []
        self.callbacks_count = []
        self.callback_current_count = 0

        # reward data
        self.rewards_created = False
        self.rewards_multi = False
        self.rewards = []
        self.reward_current = None
        self.rewards_cnt = None

        # simulation data
        self._actuators_used_set = set()  # keep track of what EMS actuators are actually actuated
        self.simulation_success = 1  # 1 fail, 0 success

        print('\n*NOTE: Simulation EmsPy class and instance created!')

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
            if ems_tc is not None and ems_tc:  # catch 'None' and '{}' input for TC:
                for ems_name in ems_tc:
                    if ems_name in self.ems_names_master_list:
                        raise ValueError(f'ERROR: EMS metric user-defined names must be unique, '
                                         f'{ems_name}({self.ems_type_dict[ems_name]}) != {ems_name}({ems_type})')
                    setattr(self, 'handle_' + ems_type + '_' + ems_name, None)
                    setattr(self, 'data_' + ems_type + '_' + ems_name, [])
                    if ems_type == 'actuator':  # handle associated actuator setpoints
                        setpoint_name = 'setpoint_' + ems_name
                        setattr(self, 'data_' + setpoint_name, [])  # what user/control sets
                        self.ems_type_dict[setpoint_name] = 'setpoint'
                        self.ems_names_master_list.append(setpoint_name)
                    self.ems_type_dict[ems_name] = ems_type
                    self.ems_names_master_list.append(ems_name)  # all ems metrics collected
                self.ems_num_dict[ems_type] = len(ems_tc)  # num of metrics per ems category
                self.df_count += 1
        # handle available timing data dict type
        for t in self.times_master_list:
            self.ems_type_dict[t] = 'time'

    def _init_weather_data(self):
        """Creates and initializes the necessary instance attributes given by the user for present weather metrics."""

        if self.tc_weather is not None and self.tc_weather:  # catch 'None' and '{}' input for Weather TC
            # verify provided weather ToC is accurate/acceptable
            for weather_name, weather_metric in self.tc_weather.items():
                if weather_metric not in EmsPy.available_weather_metrics:
                    raise Exception(f'ERROR: [{weather_metric}] weather metric is misspelled or not provided by'
                                    f' EnergyPlusAPI.')
                if weather_name in self.ems_names_master_list:
                    raise ValueError(f'ERROR: EMS metric user-defined names must be unique, '
                                     f'{weather_name}({self.ems_type_dict[weather_name]}) != {weather_name}(weather)')
                setattr(self, 'data_weather_' + weather_name, [])
                self.ems_names_master_list.append(weather_name)
                self.ems_type_dict[weather_name] = 'weather'
            self.ems_num_dict['weather'] = len(self.tc_weather)
            self.df_count += 1

    def _init_timestep(self) -> int:
        """This function is used to fetch the timestep input from the IDF model & verify with user input."""

        # returns fractional hour, convert to timestep/hr
        try:
            # TODO determine robustness of the api.exchange function - IT IS NOT (20 defaults to 60 etc)
            timestep = int(1 // self.api.exchange.zone_time_step(self.state))
            available_timesteps = [1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60]
            if timestep in available_timesteps:
                if timestep != self.timestep_input:
                    # TODO add traceback
                    raise SystemExit(f'User input timestep [{self.timestep_input}] must equal the model timestep '
                                     f'of [{timestep}]. Please check your IDF.\nAvailable timesteps are '
                                     f'{available_timesteps}')
                self.timestep_period = 60 // timestep
                self.timestep_per_hour = timestep
                print(f'\n*NOTE: Your simulation timestep period is {self.timestep_period} minutes @ {timestep}'
                      f' timestep(s) an hour.\n')
                self.timestep_params_initialized = True
                return timestep
        except ZeroDivisionError:
            pass

    def _init_reward(self, reward):
        """This updates the reward attributes to the needs set by user."""

        # attribute creation
        if not self.rewards_created:  # first iteration, do once
            try:  # multi obj rewards
                self.rewards_cnt = len(reward)
                self.rewards_multi = True
                self.rewards = [[] for _ in range(self.rewards_cnt)]
            except TypeError:
                self.rewards_cnt = 1
                self.rewards = []
            self.rewards_created = True
            self.reward_current = [0] * self.rewards_cnt

    def _set_ems_handles(self):
        """Gets and reassigns the gathered sensor/actuators handles to their according _handle instance attribute."""

        ems_types = ['var', 'intvar', 'meter', 'actuator']
        for ems_type in ems_types:
            ems_tc = getattr(self, 'tc_' + ems_type)
            if ems_tc is not None:
                for name in ems_tc:
                    handle_inputs = ems_tc[name]
                    setattr(self, 'handle_' + ems_type + '_' + name, self._get_handle(ems_type, handle_inputs))
        print('\n*NOTE: Got all EMS handles.\n')

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
            if ems_type == 'var':
                handle = datax.get_variable_handle(state,
                                                   ems_obj_details[0],  # var name
                                                   ems_obj_details[1])  # var key
            elif ems_type == 'intvar':
                handle = datax.get_internal_variable_handle(state,
                                                            ems_obj_details[0],  # int var name
                                                            ems_obj_details[1])  # int var key
            elif ems_type == 'meter':
                handle = datax.get_meter_handle(state,
                                                ems_obj_details)  # meter name
            elif ems_type == 'actuator':
                handle = datax.get_actuator_handle(state,
                                                   ems_obj_details[0],  # component type
                                                   ems_obj_details[1],  # control type
                                                   ems_obj_details[2])  # actuator key
            # catch error handling by EMS E+
            if handle == -1:
                raise Exception(f'ERROR: [{str(ems_obj_details)}]: The EMS sensor/actuator handle could not be'
                                ' found. Please consult the .idf and/or your ToC for accuracy')
            else:
                return handle
        except IndexError:
            raise IndexError(f'ERROR: [{str(ems_obj_details)}]: This [{ems_type}] object does not have all the '
                             f'required fields to get the EMS handle')

    def _update_time(self):
        """Updates all time-keeping and simulation timestep attributes of running simulation."""

        state = self.state
        datax = self.api.exchange

        # gather data
        year = datax.year(state)
        month = datax.month(state)
        day = datax.day_of_month(state)
        hour = datax.hour(state)
        minute = datax.minutes(state)
        timestep_zone_num = datax.zone_time_step_number(state)

        # set, append
        self.actual_date_times.append(datax.actual_date_time(state))
        self.actual_times.append(datax.actual_time(state))
        self.current_times.append(datax.current_time(state))
        self.years.append(year)
        self.months.append(month)
        self.days.append(day)
        self.hours.append(hour)
        self.minutes.append(minute)
        # timesteps
        self.timesteps_zone_num.append(timestep_zone_num)
        self.timestep_zone_num_current = timestep_zone_num

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
        self.ems_current_data_dict['Datetime'] = dt  # TODO not used

        # timesteps total
        if len(self.time_x) < 2 or \
                self.time_x[-1] != self.time_x[-2] or self.timesteps_zone_num[-1] != self.timesteps_zone_num[-2]:
            # verify new timestep if current & previous timestep num and datetime are different
            self.timestep_total_count += 1

    def _update_ems_data_attributes(self, ems_type: str, ems_name: str, data_val: float):
        """Helper function to update EMS attributes with current values."""

        getattr(self, 'data_' + ems_type + '_' + ems_name).append(data_val)
        self.ems_current_data_dict[ems_name] = data_val

    def _update_ems_and_weather_vals(self, ems_metrics_list: list):
        """Fetches and updates given sensor/actuator/weather values to data lists/dicts from running simulation."""

        # TODO how to handle user-specified TIMING updates separate from state, right now they are joint
        # specific data exchange API function calls
        datax = self.api.exchange
        ems_datax_func = {'var': datax.get_variable_value,
                          'intvar': datax.get_internal_variable_value,
                          'meter': datax.get_meter_value,
                          'actuator': datax.get_actuator_value}

        for ems_name in ems_metrics_list:
            ems_type = self.ems_type_dict[ems_name]
            # SKIP time and setpoint updates, each have their OWN updates
            if ems_type == 'time' or ems_type == 'setpoint':
                continue
            if ems_type == 'weather':
                data_i = self._get_weather([ems_name], 'today', self.hours[-1], self.timestep_zone_num_current)
            elif ems_type == 'intvar':  # internal(static) vars updated ONCE, separately
                if not self.static_vars_obtained:
                    data_i = ems_datax_func[ems_type](self.state, getattr(self, 'handle_' + ems_type + '_' + ems_name))
                    self.static_vars_obtained = True
            else:  # rest: var, meter, actuator
                # get data from E+ sim
                data_i = ems_datax_func[ems_type](self.state, getattr(self, 'handle_' + ems_type + '_' + ems_name))

            # store data in obj attributes
            self._update_ems_data_attributes(ems_type, ems_name, data_i)

    def _update_reward(self, reward):
        """ Updates attributes related to the reward. Works for single-obj(scalar) and multi-obj(vector) reward fxns."""

        # handle single vs multi reward together
        if self.rewards_multi:
            rewards = []  # init for multi
        else:
            reward = [reward]  # need to make single val iterable

        for reward_i in reward:
            if type(reward_i) is not float and type(reward_i) is not int:
                raise TypeError(f'ERROR: Reward returned from the observation function, [{reward_i}] must be of'
                                f' type float or int.')
            else:
                if self.rewards_multi:
                    rewards.append(reward_i)  # [[r11, r12, r13], [r21, r22, r23], ...]
                else:
                    rewards = reward_i  # single reward
        # reward data update
        self.rewards.append(rewards)
        self.reward_current = rewards

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
            raise Exception('ERROR: Weather data must either be called from sometime today or tomorrow relative to'
                            ' current simulation timestep.')
        if hour > 24 or hour < 0:
            raise Exception('ERROR: The hour of the day cannot exceed 24 or be less than 0')
        try:
            if zone_ts > self.timestep_per_hour:
                raise Exception(f'ERROR: The desired weather forecast timestep, [{zone_ts}] cannot exceed the subhourly'
                                f' simulation timestep set for the model, [{self.timestep_per_hour}].')
        except TypeError:
            # catch error ONLY during design days when timestep has not been initialized yet
            pass
        single_metric = False
        if len(weather_metrics) is 1:
            single_metric = True

        # fetch weather
        weather_data = []
        for weather_name in weather_metrics:
            # input error handling
            if weather_name not in self.tc_weather:
                raise Exception(f'ERROR: Invalid weather metric [{weather_name}] given. Please see your weather ToC for'
                                ' available weather metrics.')

            weather_metric = self.tc_weather[weather_name]
            # sun weather type is unique to rest, doesn't follow consistent naming system
            if weather_metric is not 'sun_is_up':
                weather_data.append(getattr(self.api.exchange, when + '_weather_' + weather_metric + '_at_time')\
                                    (self.state, hour, zone_ts))
            elif weather_metric is 'sun_is_up':
                weather_data.append(self.api.exchange.sun_is_up(self.state))
        if single_metric:
            return weather_data[0]
        else:
            return weather_data

    def _actuate(self, actuator_handle: str, actuator_val):
        """Sets value of a specific actuator in running simulation, or relinquishes control back to EnergyPlus."""

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
        :param actuator_setpoint_dict: dict of actuator name keys (str) & associated setpoint val. A setpoint of None
        returns control back to EnergyPlus from EMS
        """
        if actuator_setpoint_dict is not None:  # in case some 'actuation functions' does not actually act
            for actuator_name, actuator_setpoint in actuator_setpoint_dict.items():
                if actuator_name not in self.tc_actuator:
                    raise Exception(f'ERROR: Either this actuator [{actuator_name}] is not tracked, or misspelled.'
                                    f' Check your Actuator ToC.')
                # actuate and update data tracking
                actuator_handle = getattr(self, 'handle_actuator_' + actuator_name)
                self._actuate(actuator_handle, actuator_setpoint)
                self._actuators_used_set.add(actuator_name)  # to keep track of what actuators from TC are actually used
                # update SETPOINT value of actuators
                getattr(self, 'data_setpoint_' + actuator_name).append(actuator_setpoint)
        else:
            print(f'\n*NOTE: No actuators/values defined for actuation function at calling point [{calling_point}],'
                  f' timestep [{self.timestep_zone_num_current}]\n')

    def _enclosing_callback(self, calling_point: str, observation_fxn, actuation_fxn,
                            update_state: bool = False,
                            update_state_freq: int = 1,
                            update_act_freq: int = 1):
        """
        Decorates the main callback function to set the user-defined calling point and set timing and data params.

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
            The callback function passed to the running EnergyPlus simulation, this commands the runtime interaction.

            :param state_arg: NOT USED by this API - passed to and used internally by EnergyPlus simulation
            """
            # get EMS handles ONCE
            if not self.got_ems_handles:
                # verify ems objects are ready for access, skip until
                if not self.api.exchange.api_data_fully_ready(state_arg):
                    return
                self._set_ems_handles()
                self.got_ems_handles = True

            # skip if simulation in WARMUP
            if self.api.exchange.warmup_flag(state_arg):
                return

            # init Timestep params ONCE, after warmup and EMS handles
            if not self.timestep_params_initialized:
                self._init_timestep()

            # get current timestep for update frequency
            self.timestep_zone_num_current = self.api.exchange.zone_time_step_number(state_arg)
            current_timestep = self.timestep_zone_num_current  # preserve for callback # TODO implement

            # TODO verify this is proper way to prevent sub-timestep callbacks, make seperate function
            # FAIL with multiple CPs since they share timesteps
            # catch and skip sub-timestep callbacks, when the timestep num is the same as before
            try:
                if self.timesteps_zone_num[-1] == self.timestep_zone_num_current:
                    # verify with (timestep/hr) * (24 hrs) * (# of days of sim) == data/df length
                    # print('-- Sub-Timestep Callback --')
                    # return  # skip callback
                    pass
            except IndexError:
                pass  # catch first iter when no data available

            # state update & observation (optionally)
            if update_state and self.timestep_zone_num_current % update_state_freq == 0:
                # update & append simulation data
                self._update_time()  # note timing update is first
                self._update_ems_and_weather_vals(self.ems_names_master_list)  # update sensor/actuator/weather/ vals
                self.callback_calling_points.append(calling_point)
                # run user-defined agent state update function
                if observation_fxn is not None:
                    reward = observation_fxn()  # execute user's state/reward observation
                    if reward is not None:  # reward returned
                        if not self.rewards_created:
                            self._init_reward(reward)
                        self._update_reward(reward)

            # action update
            if actuation_fxn is not None and self.timestep_zone_num_current % update_act_freq == 0:
                self._actuate_from_list(calling_point, actuation_fxn())

            # init and update CUSTOM dataframes
            if not self.custom_dataframes_initialized:
                self._init_custom_dataframe_dict()
                self.custom_dataframes_initialized = True
            self._update_custom_dataframe_dicts(calling_point)

            # update callback count data
            self.callback_current_count += 1
            self.callbacks_count.append(self.callback_current_count)

        return _callback_function

    def _init_calling_points_and_callback_functions(self):
        """This iterates through the Calling Point Dict{} to set runtime calling points with actuation functions."""

        for calling_key in self.calling_point_actuation_dict:
            # check if user-specified calling point is correct and available
            if calling_key not in self.available_calling_points:
                raise Exception(f'ERROR: The calling point [{calling_key}] is not a valid calling point. Please see'
                                f' the Python API 0.2 documentation and available calling point list: '
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
                # report message summary to user
                actuation_msg = 'Yes' if actuation_fxn is not None else 'No'
                observation_msg = 'Yes' if observation_fxn is not None else 'No'
                print(f'\n*NOTE: Callback Function Summary: Calling Point [{calling_key}]\n'
                      f'       Actuation: [{actuation_msg}], Observation: [{observation_msg}], '
                      f'State Update: [{update_state}], State Update Freq: [{update_state_freq}], '
                      f'Action Update Freq: [{update_act_freq}]')

    def _create_default_dataframes(self):
        """Creates default dataframes for each EMS data list, for each EMS category (and rewards if included in sim)."""

        if not self.ems_num_dict:
            return  # no ems dicts created, very unlikely
        for ems_type in self.ems_num_dict:
            ems_df_dict = {'Datetime': self.time_x, 'Timestep': self.timesteps_zone_num,
                           'Calling Point': self.callback_calling_points}  # index columns
            for ems_name in getattr(self, 'tc_' + ems_type):
                ems_data_list_name = 'data_' + ems_type + '_' + ems_name
                try:
                    ems_df_dict[ems_name] = getattr(self, ems_data_list_name)
                except AttributeError:
                    pass  # ignore unused actuators
            # create default df
            df_name = 'df_' + ems_type
            setattr(self, df_name, pd.DataFrame.from_dict(ems_df_dict))

        # manage rewards separately, since not standard EMS metrics
        if self.rewards:
            col_names = ['reward']  # single reward
            if self.rewards_multi:
                col_names = []
                for n in range(self.rewards_cnt):
                    col_names.append('reward' + str(n + 1))
            self.df_reward = pd.DataFrame(self.rewards, columns=col_names)
            # self.df_reward = self.df_reward.dropna()  # drop NA vals # TODO figure out why these are here at the start
            # add times to df  # TODO issue with multi obj reward
            self.df_reward['Datetime'] = self.time_x
            self.df_reward['Timestep'] = self.timesteps_zone_num
            self.df_reward['Calling Point'] = self.callback_calling_points

    def _init_custom_dataframe_dict(self):
        """Initializes custom EMS metric dataframes attributes at specific calling points & frequencies."""

        # add to dataframe  to fetch & track data during sim
        for df_name in self.df_custom_dict:
            ems_metrics, calling_point, update_freq = self.df_custom_dict[df_name]
            self.df_count += 1
            if calling_point not in self.calling_point_actuation_dict:
                raise Exception(f'ERROR: Invalid Calling Point name [{calling_point}].\nSee your declared available'
                                f' calling points {self.calling_point_actuation_dict.keys()}.')
            # metric names must align with the EMS metric names assigned in var, intvar, meters, actuators, weather ToC
            ems_custom_dict = {'Datetime': [], 'Timestep': []}
            # handle reward tracking
            if self.rewards:
                is_reward = 'rewards'
            else:
                is_reward = ''
            for metric in ems_metrics:
                # verify proper input
                if metric not in self.ems_names_master_list + [is_reward]:
                    raise Exception(f'ERROR: Incorrect EMS metric name, [{metric}], was entered for custom '
                                    f'dataframes.')
                # unused actuators
                if metric in self.tc_actuator and metric not in self._actuators_used_set:
                    raise Exception('ERROR: The EMS actuator [{metric}] was not by user and has no data to track.')
                # create dict to collect data for pandas dataframe
                if metric == 'rewards' and self.rewards_multi:  # multiple reward
                    for i in range(self.rewards_cnt):
                        metric = 'reward' + str(i + 1)  # reward#, 1-n
                        ems_custom_dict[metric] = []
                else:
                    ems_custom_dict[metric] = []  # single reward, all else EMS
            # update custom df tracking list
            self.df_custom_dict[df_name][0] = ems_custom_dict

    def _update_custom_dataframe_dicts(self, calling_point):
        """Updates dataframe data based on desired calling point, timestep frequency, and specific ems vars."""

        # TODO handle redundant data collection when cp & freq are identical to default (may not always be applicable)
        if not self.df_custom_dict:
            return  # no custom dicts created
        # iterate through and update all default and user-defined dataframes
        for df_name in self.df_custom_dict:
            ems_dict, cp, update_freq = self.df_custom_dict[df_name]  # unpack value
            if cp is calling_point and self.timestep_zone_num_current % update_freq == 0:
                reward_index = 0  # TODO make independent of perfect order of reward, make robust to reward name int
                for ems_name in ems_dict:
                    # get most recent data point
                    if ems_name is 'Datetime':
                        data_i = self.time_x[-1]
                    elif ems_name is 'Timestep':
                        data_i = self.timesteps_zone_num[-1]
                    elif 'reward' in ems_name:
                        if self.rewards_multi:
                            data_i = self.rewards[-1][reward_index]  # extra ith reward of most recent reward
                            reward_index += 1
                        else:
                            data_i = self.rewards[-1]
                    else:
                        # normal ems types
                        ems_type = self.get_ems_type(ems_name)
                        if ems_type == 'setpoint':  # actuator setpoints
                            data_list_name = 'data_' + ems_name  # setpoint is redundant, user must input themselves
                        else:  # all other
                            data_list_name = 'data_' + ems_type + '_' + ems_name
                        data_i = getattr(self, data_list_name)[-1]

                    # append to dict list
                    self.df_custom_dict[df_name][0][ems_name].append(data_i)

    def _create_custom_dataframes(self):
        """Creates custom dataframes for specifically tracked ems data list, for each ems category."""

        if not self.df_custom_dict:
            print('*NOTE: No custom dataframes created.')
            return  # no ems dicts created
        for df_name in self.df_custom_dict:
            ems_dict, _, _ = self.df_custom_dict[df_name]
            setattr(self, df_name, pd.DataFrame.from_dict(ems_dict))

    def get_ems_type(self, ems_metric: str):
        """ Returns EMS (var, intvar, meter, actuator, weather) or time type string for a given ems metric variable."""

        return self.ems_type_dict[ems_metric]  # used to create attribute var names 'data_' + type

    def _post_process_data(self):
        """Handles various cleanup of data after the simulation has ran, necessary for certain features."""

        # (1) remove data of unused actuators, if applicable
        if self.tc_actuator:
            unused_actuators = []
            for actuator_name in self.tc_actuator:
                if actuator_name not in self._actuators_used_set:
                    print(f"*NOTE: The actuator [{actuator_name}] was not used by EMS to actuator. Their EMS tracked "
                          f"null data attributes will be removed.")
                    # remove their data attributes
                    delattr(self, 'data_actuator_' + actuator_name)
                    unused_actuators.append(actuator_name)
            # update EMS number dictionary - relates to default DF creation,
            original_num = self.ems_num_dict['actuator']
            unused_num = len(unused_actuators)
            updated_num = original_num - unused_num
            # report to user
            if updated_num == 0:  # last actuator left
                self.ems_num_dict.pop('actuator')
                print(f'*NOTE: No EMS actuators of [{original_num}] were used, all have been removed from your '
                      f'simulation object.')
            else:
                self.ems_num_dict['actuator'] = updated_num
                print(f'*NOTE: [{updated_num}] of [{original_num}] actuators were used in this simulation.')

    def _user_input_check(self):
        # TODO create function that checks if all user-input attributes has been specified and add help directions

        if not self.calling_point_actuation_dict:
            print('\n*WARNING: No calling points or callback actuation/observation functions were initialized.'
                  'Will just run simulation!\n')

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

        # create callback function(s) and link with calling point(s)
        if self.calling_point_actuation_dict:
            self._init_calling_points_and_callback_functions()

        # RUN SIMULATION
        print('\n* * * Running E+ Simulation * * *\n')
        self.simulation_success = self.api.runtime.run_energyplus(self.state, ['-w', weather_file, '-d', 'out', self.idf_file])   # cmd line args
        if self.simulation_success != 0:
            print('\n* * * Simulation FAILED * * *\n')
        # simulation successful
        else:
            print('\n* * * Simulation Done * * *')
            self._post_process_data()
            # create default and custom ems pandas df's after simulation complete
            self._create_default_dataframes()
            self._create_custom_dataframes()
            print('* * * DF Creation Done * * *')


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
        self.ems_list_update_checked = False # TODO get rid off, doesnt work with multiple method instances

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
        :param update_state: whether EMS and time/timestep should be updated.
        :param update_state_freq: the number of zone timesteps per updating the simulation state
        :param update_act_freq: the number of zone timesteps per updating the actuators from the actuation function
        """

        if update_act_freq > update_state_freq:
            print(f'\n*WARNING: It is unusual to have your action update more frequent than your state update\n')
        if calling_point in self.calling_point_actuation_dict:  # overwrite error
            raise Exception(
                f'ERROR: You have overwritten the calling point \'{calling_point}\'. Keep calling points unique.')
        else:
            self.calling_point_actuation_dict[calling_point] = [observation_fxn, actuation_fxn, update_state,
                                                                update_state_freq, update_act_freq]

    def _check_ems_metric_input(self, ems_metric):
        """Verifies user-input of EMS metric/type list is valid."""

        # catch EMS type names (var, intvar, actuator, etc.)
        if ems_metric in self.ems_num_dict:
            raise Exception(f'ERROR: EMS categories can only be called by themselves, please only call one at a '
                            f'time.')
        # catch invalid EMS metric names
        elif ems_metric not in self.ems_names_master_list and ems_metric not in self.times_master_list:
            raise Exception(f'ERROR: The EMS/timing metric [{ems_metric}] is not valid. Please see your EMS ToCs'
                            f' or EmsPy.ems_master_list & EmsPy.times_master_list for available EMS & '
                            f'timing metrics')

    def get_ems_data(self, ems_metric_list: list, time_rev_index: list = [0]) -> list:
        """
        This takes desired EMS metric(s) (or type) & returns the entire current data set(s) OR at specific time indices.

        This function should be used to collect user-defined state space OR time information at each timestep. 1 to all
        EMS metrics and timing can be called, or just EMS category (var, intvar, meter, actuator, weather), and 1 data
        point to the entire current data set can be returned.
        It is likely that the user will want the most recent data point only.

        If calling any default timing data, see EmsPy.times_master_list for available timing data metrics.

        :param ems_metric_list: list of strings (or single element) of any available EMS/timing metric(s) to be called,
        or ONLY ONE entire EMS category ('var', 'intvar', 'meter', 'actuator', 'weather', 'time')
        :param time_rev_index: list (or single value) of timestep indexes, applied to all EMS/timing metrics starting
        from index 0 as most recent available data point. An empty list [] will return the entire current data list for
        each metric.
        :return return_data_list: nested list of data for each EMS metric at each time index specified, or entire list
        """

        # handle single val inputs -> convert to list for rest of function
        single_val = False
        single_metric = False
        # metrics
        if type(ems_metric_list) is not list:  # assuming single metric
            ems_metric_list = [ems_metric_list]
        if len(ems_metric_list) == 1:
            single_metric = True
        # time indexes
        if type(time_rev_index) is not list:  # assuming single time
            time_rev_index = [time_rev_index]
        if len(time_rev_index) == 1:
            single_val = True

        return_data_list = []

        # check if only EMS category called
        ems_type = ems_metric_list[0]
        if ems_type in self.ems_num_dict and single_metric:
            # reassign entire EMS type list
            if ems_type == 'time':
                ems_metric_list = self.times_master_list
            else:
                ems_metric_list = list(getattr(self, 'tc_' + ems_metric_list[0]).keys())

        for ems_metric in ems_metric_list:
            # verify valid input #TODO do once
            self._check_ems_metric_input(ems_metric)
            ems_type = self.get_ems_type(ems_metric)  # for attribute variable name
            # no time index specified, return ALL current data
            if not time_rev_index:
                return_data_list.append(getattr(self, 'data_' + ems_type + '_' + ems_metric))
            else:
                return_data_indexed = []
                # iterate through previous time indexes
                for time in time_rev_index:
                    if ems_type is not 'time':
                        ems_name = 'data_' + ems_type + '_' + ems_metric
                    else:
                        ems_name = ems_metric
                    try:
                        data_indexed = getattr(self, ems_name)[-1 - time]
                        # so that a single-element nested list is not returned
                        if single_val:
                            return_data_indexed = data_indexed
                        else:
                            return_data_indexed.append(data_indexed)
                    except IndexError:
                        print('\n*NOTE: Not enough simulation time elapsed to collect data at specified index.\n')
                # no unnecessarily nested lists
                if single_metric:
                    return return_data_indexed
                else:
                    return_data_list.append(return_data_indexed)
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

    def update_ems_data(self, ems_metric_list: list, return_data: bool):
        """
        This takes desired EMS metric(s) (or type) to update from the sim (and opt return val) at calliing point.

        This OPTIONAL function can be used to update/collect specific EMS at each timestep for a given calling point.
        One to all EMS metrics can be called, or just EMS category (var, intvar, meter, actuator, weather) and have the
        data point updated & returned. This is ONLY NEEDED if the user wants to update specific EMS metrics at a unique
        calling point separate from ALL EMS metrics if using default state update.

        This also works for default timing data.  # TODO does not work currently with _update_ems_and_weather_val

        :param ems_metric_list: list of any available EMS metric(s) to be called, or ONLY ONE entire EMS category
        (var, intvar, meter, actuator, weather) in a list
        :param return_data: Whether or not to return an order list of the data points fetched
        :return return_data_list: list of fetched data for each EMS metric at each time index specified or None
        """

        # if only EMS category called
        if ems_metric_list[0] in self.ems_num_dict and len(ems_metric_list) == 1:
            ems_metric_list = list(getattr(self, 'tc_' + ems_metric_list[0]).keys())
        else:  # TODO get rid off, doesnt work with multiple method instances
            for ems_metric in ems_metric_list:
                if not self.ems_list_update_checked:
                    self._check_ems_metric_input(ems_metric)
                    self.ems_list_update_checked = True

        self._update_ems_and_weather_vals(ems_metric_list)
        if return_data:
            return self.get_ems_data(ems_metric_list)
        else:
            return None

    def init_custom_dataframe_dict(self, df_name: str, calling_point: str, update_freq: int, ems_metrics: list):
        """
        Initialize custom EMS metric dataframes attributes at specific calling points & frequencies to be tracked.

        Desired setpoint data from actuation actions can be acquired and compared to updated system setpoints - Use
        'setpoint' + your_actuator_name as the EMS metric name. Rewards can also be fetched. These are NOT collected
        by default dataframes.

        :param df_name: user-defined df variable name
        :param calling_point: the calling point at which the df should be updated
        :param update_freq: how often data will be posted, it will be posted every X timesteps
        :param ems_metrics: list of EMS metric names, 'setpoint+...', or 'rewards', to store their data points in df
        """
        self.df_count += 1
        self.df_custom_dict[df_name] = [ems_metrics, calling_point, update_freq]

    def get_df(self, df_names: list=[], to_csv_file: str=''):
        """
        Returns selected EMS-type default dataframe based on user's entered ToC(s) or custom DF, or ALL df's by default.

        :param df_names: default EMS metric type (var, intvar, meter, actuator, weather) OR custom df name. Leave
        argument empty if you want to return ALL dataframes together (all default, then all custom)
        :param to_csv_file: path/file name you want the dataframe to be written to
        :return: (concatenation of) pandas dataframes in order of entry or [vars, intvars, meters, weather, actuator] by
        default.
        """
        if not self.calling_point_actuation_dict:
            raise Exception('ERROR: There is no dataframe data to collect and return, please specific calling point(s)'
                            ' first.')
        if self.simulation_success != 0:
            raise Exception('ERROR: Simulation must be run successfully first to fetch data. See EnergyPlus error file,'
                            ' eplusout.err')

        all_df = pd.DataFrame()  # merge all into 1 df
        return_df = {}
        # handle DEFAULT dfs
        if self.rewards:  # add reward to iterator if applicable
            df_default_names = list(self.ems_num_dict.keys()) + ['reward']
        else:
            df_default_names = self.ems_num_dict.keys()
        for df_name in df_default_names:  # iterate thru available EMS types
            if df_name in df_names or not df_names:  # specific or ALL dfs
                df = (getattr(self, 'df_' + df_name))
                return_df[df_name] = df
                # create complete DF of all default vars with only 1 set of time/index columns
                if all_df.empty:
                    all_df = df.copy(deep=True)
                else:
                    all_df = pd.merge(all_df, df, on=['Datetime', 'Timestep', 'Calling Point'])  # TODO causes issue
                if df_name in df_names:
                    df_names.remove(df_name)

        # handle CUSTOM dfs
        for df_name in self.df_custom_dict:
            if df_name in df_names or not df_names:
                df = (getattr(self, df_name))
                return_df[df_name] = df
                if all_df.empty:
                    all_df = df.copy(deep=True)
                else:  # TODO verify robustness of merging of custom df with default, can it be compressed for same time indexes
                    all_df = pd.concat([all_df, df], axis=1)
                    # TODO determine why custom dfs do not add to all_df well, num of indexes is wrong
                if df_name in df_names:
                    df_names.remove(df_name)
        # leftover dfs not fetched and returned
        if df_names:
            raise ValueError(f'ERROR: Either dataframe custom name or default type: {df_names} is not valid or was not'
                             ' collected during simulation.')
        else:
            if to_csv_file:
                all_df.to_csv(to_csv_file, index=False)
            return_df['all'] = all_df
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
