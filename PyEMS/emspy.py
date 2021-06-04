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
# from typing import Union  # TODO check Python version compatibility


class EmsPy:
    """A meta-class wrapper to the EnergyPlus Python API to simplify/constrain usage for RL-algorithm purposes."""

    available_weather_metrics = ['sun_is_up', 'is_raining', 'is_snowing', 'albedo', 'beam_solar', 'diffuse_solar',
                                 'horizontal_ir', 'liquid_precipitation', 'outdoor_barometric_pressure',
                                 'outdoor_dew_point', 'outdoor_dry_bulb', 'outdoor_relative_humidity',
                                 'sky_temperature', 'wind_direction', 'wind_speed']

    available_calling_points = ['after_component_get_input', 'after_new_environment_warmup_complete',
                                'after_predictor_after_hvac_managers', 'after_predictor_before_hvac_managers',
                                'begin_new_environment', 'begin_system_timestep_before_predictor',
                                'begin_zone_timestep_after_init_heat_balance',
                                'begin_zone_timestep_before_set_current_weather',
                                'end_system_sizing', 'end_system_after_hvac_reporting',
                                'end_system_timestep_before_hvac_reporting'
                                'end_zone_sizing', 'end_zone_timestep_after_zone_reporting',
                                'end_zone_timestep_before_zone_reporting',
                                'inside_system_iteration_loop']  # TODO verify correctness

    # TODO restrict timesteps in known range
    def __init__(self, ep_path: str, ep_idf_to_run: str, timesteps: int, calling_point_actuation_dict: {},
                 vars_tc: list, intvars_tc: list, meters_tc: list, actuators_tc: list, weather_tc: list):
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
        :param calling_point_actuation_dict: dict with calling point as key and linked actuation fxn and args as value
        :param vars_tc: list of desired output Variables, with each object provided as
        ['user_var_name', 'variable_name', 'variable_key'] within the list
        :param intvars_tc: list of desired Internal Variables (static), with each object provided as
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
        import pyenergyplus.api
        from pyenergyplus.api import EnergyPlusAPI

        self.pyapi = pyenergyplus.api
        self.api = EnergyPlusAPI()  # instantiation of Python EMS API

        # instance important below
        self.state = self._new_state()  # TODO determine if multiple state instances should be allowed (new meta attr.)
        self.idf_file = ep_idf_to_run  # E+ idf file to simulation

        # Table of Contents for EMS sensor and actuators
        self.vars_tc = vars_tc
        self.intvars_tc = intvars_tc
        self.meters_tc = meters_tc
        self.actuators_tc = actuators_tc

        # name lists
        self.var_names = []
        self.intvar_names = []
        self.meter_names = []
        self.actuator_names = []
        self.weather_names = []
        self.ems_master_list = []

        # summary dicts
        self.ems_dict = {}  # keep track of EMS variable categories and num of vars
        self.ems_current_data_dict = {}  # collection of all ems metrics (keys) and their current values (val)
        self.calling_point_actuation_dict = calling_point_actuation_dict  # links cp to actuation fxn & its needed args
        # establish runtime calling points and custom callback function specification with defined arguments
        self._set_calling_points_and_actuation_functions()

        # create attributes of sensor and actuator .idf handles and data arrays
        self._init_ems_handles_and_data()  # creates ems_handle = int & ems_data = [] attributes, and variable counts
        self.got_ems_handles = False
        self.static_vars_gathered = False  # static (internal) variables, gather once

        # Table of Content for present weather data
        self.weather_tc = weather_tc
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

        # timesteps and simulation iterations
        self.timestep_count = 0
        self.callback_count = 0
        self.zone_timestep = 1  # fluctuate from one to # of timesteps per hour # TODO how to enforce only once per ts
        self.timestep_freq = timesteps  # sim timesteps per hour # TODO enforce via OPENSTUDIO SDK
        # TODO determine proper rounding of int timesteps interval
        self.timestep_period = 60 // timesteps  # minute duration of each timestep of simulation

        # dataframes
        self.df_count = 0
        self.df_custom_dict = {}  # key: dict_name, val: ([ems_list], 'calling_point', update freq)
        self.ems_custom_type_dict = {}  # key: ems var name, val: ems category type
        self.df_vars = None
        self.df_intvars = None
        self.df_meters = None
        self.df_actuators = None
        self.weather = None
        # TODO determine if needed, if so move initialization

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
        # TODO compress repetition if still readable
        # set attribute handle names and data arrays given by user to None
        if self.vars_tc is not None:
            for var in self.vars_tc:
                var_name = var[0]
                self.var_names.append(var_name)
                setattr(self, 'handle_var_' + var_name, None)
                setattr(self, 'data_var_' + var_name, [])
            self.ems_dict['var'] = len(self.vars_tc)  # num of metrics per ems category
            self.ems_master_list = self.ems_master_list + self.vars_tc  # all ems metrics collected
            self.df_count += 1

        if self.intvars_tc is not None:
            for intvar in self.intvars_tc:
                intvar_name = intvar[0]
                self.intvar_names.append(intvar_name)
                setattr(self, 'handle_intvar_' + intvar_name, None)
                setattr(self, 'data_intvar_' + intvar_name, None)  # static val
            self.ems_dict['intvar'] = len(self.intvars_tc)
            self.ems_master_list = self.ems_master_list + self.intvars_tc
            self.df_count += 1

        if self.meters_tc is not None:
            for meter in self.meters_tc:
                meter_name = meter[0]
                self.meter_names.append(meter_name)
                setattr(self, 'handle_meter_' + meter_name, None)
                setattr(self, 'data_meter_' + meter_name, [])
            self.ems_dict['meter'] = len(self.meters_tc)
            self.ems_master_list = self.ems_master_list + self.meters_tc
            self.df_count += 1

        if self.actuators_tc is not None:
            for actuator in self.actuators_tc:
                actuator_name = actuator[0]
                self.actuator_names.append(actuator_name)
                setattr(self, 'handle_actuator_' + actuator_name, None)
                setattr(self, 'data_actuator_' + actuator_name, [])
            self.ems_dict['actuator'] = len(self.actuators_tc)
            self.ems_master_list = self.ems_master_list + self.actuators_tc
            self.df_count += 1

    def _init_weather_data(self):
        """Creates and initializes the necessary instance attributes given by the user for present weather metrics."""

        # verify provided weather ToC is accurate/acceptable
        for weather_metric in self.weather_tc:
            if weather_metric not in EmsPy.available_weather_metrics:
                raise Exception(f'{weather_metric} weather metric is misspelled or not provided by EnergyPlusAPI.')
        if self.weather_tc is not None:
            for weather_type in self.weather_tc:
                self.weather_names.append(weather_type)
                setattr(self, 'data_weather_' + weather_type, [])
            self.ems_dict['weather'] = len(self.weather_tc)
            self.ems_master_list = self.ems_master_list + self.weather_tc
            self.df_count += 1

    def _set_ems_handles(self):
        """Gets and reassigns the gathered sensor/actuators handles to their according _handle instance attribute."""

        if self.vars_tc is not None:
            for var in self.vars_tc:
                setattr(self, 'handle_var_' + var[0], self._get_handle('var', var))
        if self.intvars_tc is not None:
            for intvar in self.intvars_tc:
                setattr(self, 'handle_intvar_' + intvar[0], self._get_handle('intvar', intvar))
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
            elif ems_type is 'intvar':
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
        # time keeping dataframe management
        dt = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute)
        dt += timedelta
        self.time_x.append(dt)
        self.ems_current_data_dict['Datetime'] = dt

        # manage timestep update
        # TODO make dependent on input file OR handle mistake where user enters incorrect ts
        self.timestep_count += 1  # TODO should this be done once per timestep or callback
        if self.zone_timestep > self.timestep_freq:
            self.zone_timestep = 1
        else:
            self.zone_timestep += 1

    def _update_ems_vals(self):
        """Updates and appends given sensor/actuator values to data lists/dicts from running simulation."""

        state = self.state
        datax = self.api.exchange
        if self.vars_tc is not None:
            for var in self.vars_tc:
                data_i = datax.get_variable_value(state, getattr(self, 'handle_var_' + var[0]))
                getattr(self, 'data_var_' + var[0]).append(data_i)
                self. ems_current_data_dict[var] = data_i
        if self.meters_tc is not None:
            for meter in self.meters_tc:
                data_i = datax.get_meter_value(state, getattr(self, 'handle_meter_' + meter[0]))
                getattr(self, 'data_meter_' + meter[0]).append(data_i)
                self.ems_current_data_dict[meter] = data_i
        if self.actuators_tc is not None:
            for actuator in self.actuators_tc:
                data_i = datax.get_actuator_value(state, getattr(self, 'handle_actuator_' + actuator[0]))
                getattr(self, 'data_actuator_' + actuator[0]).append(data_i)
                self.ems_current_data_dict[actuator] = data_i
        # update static (internal) variables ONCE
        if self.intvars_tc is not None and not self.static_vars_gathered:
            for intvar in self.intvars_tc:
                data_i = datax.get_internal_variable_value(state, getattr(self, 'handle_intvar_' + intvar[0]))
                getattr(self, 'data_intvar_' + intvar[0]).append(data_i)
                self.ems_current_data_dict[intvar] = data_i  # doesn't track intvars, they don't change
                self.static_vars_gathered = True

    def _update_weather_vals(self):
        """Updates and appends given weather metric values to data lists/dicts from running simulation."""

        if self.weather_tc is not None:
            for weather_type in self.weather_tc:
                data_i = self._get_weather('today', weather_type, self.hours[-1], self.zone_timestep)
                getattr(self, 'data_weather_' + weather_type).append(data_i)
                self.ems_current_data_dict[weather_type] = data_i

    def _get_weather(self, when: str, weather_metric: str, hour: int, zone_ts: int):
        """
        Gets desired weather metric data for a given hour and zone timestep, either for today or tomorrow in simulation.

        :param when: the day in question, 'today' or 'tomorrow'
        :param weather_metric: the weather metric to call from EnergyPlusAPI, only specific fields are granted
        :param hour: the hour of the day to call the weather value
        :param zone_ts: the zone timestep of the given hour to call the weather value
        """
        if weather_metric is not 'sun_is_up':
            return getattr(self.api.exchange, when + '_weather_' + weather_metric + '_at_time') \
                (self.state, hour, zone_ts)
        elif weather_metric is 'sun_is_up':  # doesn't follow consistent naming system
            return self.api.exchange.sun_is_up(self.state)

    def _actuate(self, actuator_handle: str, actuator_val):
        """ Sets value of a specific actuator in running simulator, or relinquishes control back to EnergyPlus."""
        # use None to relinquish control
        # TODO should I handle out-of-range actuator values??? (can this be managed with auto internal var lookup?)
        if actuator_val is None:
            self.api.exchange.reset_actuator(self.state, actuator_handle)  # return actuator control to EnergyPlus
        else:
            self.api.exchange.set_actuator_value(self.state, actuator_handle, actuator_val)

    def _actuate_from_list(self, actuator_pairs_list: list):
        """
        This iterates through list of actuator name and value setpoint pairs to be set in simulation.

        CAUTION: Actuation functions written by user must return an actuator_name-value pair list [[actuator1, val1],..

        :param actuator_pairs_list: list of actuator name(str) & value(float) pairs [[actuator1, val1],...]
        """
        if actuator_pairs_list is not None:  # in case some 'actuation functions' does not actually act
            for actuator_name, actuator_val in actuator_pairs_list:
                if actuator_name not in self.actuator_names:
                    raise Exception(f'Either this actuator {actuator_name} is not tracked, or misspelled.'
                                    f'Check your Actuator ToC.')
                actuator_handle = getattr(self, 'handle_actuator_' + actuator_name)
                self._actuate(actuator_handle, actuator_val)
                self.ems_current_data_dict[actuator_name] = actuator_val

    def _enclosing_callback(self, calling_point: str, actuation_fxn, update_state: bool,
                            update_state_freq: int = 1, update_act_freq: int = 1):
        """
        Decorates the main callback function to set the user-defined calling function and set timing and data params.

        # TODO specify Warning documentation and find a way to check if only one data/timing update is done per timestep
        :param calling_point: the calling point at which the callback function will be called during simulation runtime
        :param actuation_fxn: the user defined actuation function to be called at runtime
        :param update_state: whether EMS and time/timestep should be updated. This should only be done once a timestep
        :param update_state_freq: the number of zone timesteps per updating the simulation state
        :param update_act_freq: the numer of zone timesteps per updating the actuators from the actuation function
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
            if update_state and self.zone_timestep % update_state_freq == 0:
                # update & append simulation data
                self._update_time()  # note timing update is first
                self._update_ems_vals()  # update all but actuators
                self._update_weather_vals()

            # TODO verify freq robustness
            if actuation_fxn is not None and self.zone_timestep & update_act_freq == 0:
                self._actuate_from_list(actuation_fxn())

            # update custom dataframes
            self._update_custom_dataframe_dicts(calling_point)
            self.callback_count += 1

        # TODO verify if this separate timestep update can be omitted and just included in timing
        # update times at end
        # if update_timestep:
        #     self.count += 1
        #     self.zone_ts += 1
        #     if self.zone_ts > self.timestep_freq:
        #         self.zone_ts = 1

        return _callback_function

    def _set_calling_points_and_actuation_functions(self):
        """This iterates through the Calling Point Dict{} to set runtime calling points with actuation functions."""

        if not self.calling_point_actuation_dict:
            raise Exception('Your Calling Point dict is empty, please see documentation and define it before running'
                            ' simulation.')

        for calling_key in self.calling_point_actuation_dict:
            # check if user-specified calling point is correct and available
            if calling_key[9:] not in self.available_calling_points: # remove 'callback_'
                raise Exception(f'This calling point "{calling_key}" is not a valid calling point. Please see the'
                                f' Python API documentation and available calling point list class attribute.')
            else:
                # unpack actuation and fxn arguments
                unpack = self.calling_point_actuation_dict[calling_key]
                actuation_fxn, update_state, update_state_freq, update_act_freq = unpack
                # establish calling points at runtime and create/pass its custom callback function
                getattr(self.api.runtime, calling_key)(self.state, self._enclosing_callback(calling_key,
                                                                                            actuation_fxn,
                                                                                            update_state_freq,
                                                                                            update_act_freq))

    def init_custom_dataframe(self, df_name: str, calling_point: str, update_freq: int, ems_metrics: list):
        """
        Used to initialize EMS metric pandas dataframe attributes and validates proper user input.

        :param df_name: user-defined df variable name
        :param calling_point: the calling point at which the df should be updated
        :param update_freq: how often data will be posted, it will be posted every X timesteps
        :param ems_metrics: list of EMS metric var names to store their data points in df
        """

        if calling_point not in self.calling_point_actuation_dict:
            raise Exception(f'Invalid Calling Point name. Please see your available calling points '
                            f'{self.calling_point_actuation_dict}.')
        # metric names must align with the EMS metric names assigned in var, intvar, meters, actuators, weather ToC's
        ems_custom_dict = {'Datetime':[]}
        for metric in ems_metrics:
            ems_type = ''
            if metric not in self.ems_master_list:
                raise Exception('Incorrect EMS metric names were entered for positing CSV data.')
            if metric in self.var_names:
                ems_type = 'var'
            elif metric in self.intvar_names:
                ems_type = 'intvar'
            elif metric in self.meter_names:
                ems_type = 'meter'
            elif metric in self.actuator_names:
                ems_type = 'actuator'
            elif metric in self.weather_names:
                ems_type = 'weather'
            self.ems_custom_type_dict[metric] = ems_type
            # create dict to collect data for pandas dataframe
            ems_custom_dict[metric] = []
        # add to dataframe dict
        self.df_custom_dict[df_name] = (ems_custom_dict, calling_point, update_freq)
        self.df_count += 1

    def _update_custom_dataframe_dicts(self, calling_point):
        """Updates data based on desired calling point, frequency, and specific ems vars."""
        if self.df_custom_dict:
            return  # no custom dicts created
        # iterate through and update all default and user-defined dataframes
        for df_name in self.df_custom_dict:
            ems_dict, cp, update_freq = self.df_custom_dict[df_name]
            # TODO verify if % mod is robust enough for interval collection
            if cp is calling_point and self.timestep_count % update_freq is 0:
                # TODO will this update, pass by reference????
                for ems_metric in ems_dict:
                    # get most recent data point
                    ems_type = self.ems_custom_type_dict[ems_metric]
                    data_list_name = 'data_' + ems_type + '_' + ems_metric
                    data_i = getattr(self, data_list_name)[-1]
                    # append to dict list # TODO will this store
                    ems_dict[ems_metric].append(data_i)

    def _create_custom_dataframes(self, calling_point: str):
        """Creates custom dataframes for specifically tracked ems data list, for each ems category."""

        if not self.df_custom_dict:
            return  # no ems dicts created, very unlikely
        for df_name in self.df_custom_dict:
            ems_dict, _, _ = self.df_custom_dict[df_name]
            ems_dict['Datetime'] = self.time_x  # add time info
            setattr(self, df_name, pd.DataFrame.from_dict(ems_dict))

    def _create_default_dataframes(self):
        """Creates default dataframes for each ems data list, for each ems category."""

        if self.ems_dict:
            return  # no ems dicts created, very unlikely
        ems_dict = {'Datetime': self.time_x}
        for ems_type in self.ems_dict:
            for ems_name in getattr(self, ems_type + '_names'):
                ems_data_list_name = 'data_' + ems_type + '_' + ems_name
                ems_dict[ems_name] = getattr(self, ems_data_list_name)
            # create default df
            df_name = 'df_' + ems_type
            setattr(self, df_name, pd.DataFrame.from_dict(ems_dict))

    def _user_input_check(self):
        # TODO create function that checks if all user-input attributes has been specified and add help directions
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

    def run_simulation(self, weather_file):
        """This runs the EnergyPlus simulation and RL experiment."""

        # check valid input by user
        self._user_input_check()
        # RUN SIMULATION
        print('* * * Running E+ Simulation * * *')
        self.api.runtime.run_energyplus(self.state,  # cmd line arguments
                                        [
                                            '-w', weather_file,
                                            '-d', 'out',
                                            self.idf_file
                                        ]
                                        )
        # create default and custom ems pandas df's after simulation complete
        self._create_default_dataframes()
        self._create_custom_dataframes()

# TODO TYPE HINTING
# actuator_name_val_pair_list = list[list[str, int]]


class BcaEnv(EmsPy):
    # Building Control Agent (BCA) for env

    def __init__(self, ep_path: str, ep_idf_to_run: str, timesteps: int, calling_point_actuation_dict: {},
                 vars_tc: list, intvars_tc: list, meters_tc: list, actuators_tc: list, weather_tc: list):
        # follow same init procedure as parent class EmsPy
        super().__init__(ep_path, ep_idf_to_run, timesteps, calling_point_actuation_dict, vars_tc, intvars_tc,
                         meters_tc, actuators_tc, weather_tc)

    # TODO update if needed
    def get_observation(self, ems_category: str, t_back: int = 0) -> list:
        # returns data of given ems category ordered by ToC ordering
        if ems_category not in self.ems_dict:
            raise ValueError('The observation category specified is incorrect, please see method documentation.')
        data_i_t = []
        for var_i_t in range(self.ems_dict.get(ems_category)):
            var_name = getattr(self, ems_category + '_names')[var_i_t]
            data = (getattr(self, var_name + '_data'))[-1 - t_back]  # get data from end of list
            data_i_t.append(data)
        return data_i_t

    def get_weather_forecast(self, when: str, weather_metric: str, hour: int, zone_ts: int):
        return self._get_weather(when, weather_metric, hour, zone_ts)

    def run_env(self, weather_file: str):
        self.run_simulation(weather_file)
        pass


class DataDashboard:
    def __init__(self):
        pass


class EnergyPlusModel:
    # TODO figure out what idf and osm manipulation should be granted to user, or should they just do all this
    # or use openstudio package
    def __init__(self):
        pass
