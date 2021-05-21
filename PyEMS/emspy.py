import sys
import datetime

class EmsPy:

    def __init__(self, ep_path, ep_idf_to_run, vars_tc=None, int_vars_tc=None, meters_tc=None, actuators_tc=None,
                 weather_tc=None):
        sys.path.insert(0, ep_path)  # set path to E+
        from pyenergyplus.api import EnergyPlusAPI
        self.api = EnergyPlusAPI()  # instantiation of Python EMS API
        self.state = self.api.state_manager.new_state()
        # TODO likely get rid of
        # self.bca = self.BcaEnv()  # instantiation of RL agent obj, inner class
        # self.ddash = self.DataDashboard()  # instantiation of data visualization obj, inner class


        self.idf_path = ep_idf_to_run  # E+ idf file to simulation

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
        self.sys_ts = 0
        self.zone_ts = 0  # TODO what to track?


    def _reset_state(self):
        self.api.reset_state(self.state)


    def _delete_state(self):
        self.api.delete_state(self.state)


    def _init_ems_handles_and_data(self):
        """
        Initialize all the instance attribute names given by the user for the sensors/actuators to be called
        :param variables_dict:
        :param internals_dict:
        :param actuators_dict:
        :return:
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
                setattr(self, var[0], self._get_handle(state_arg, 'var', var))
        if self.int_vars_tc is not None:
            for int_var in self.int_vars_tc:
                setattr(self, int_var[0], self._get_handle(state_arg, 'int_var', int_var))
        if self.meters_tc is not None:
            for meter in self.meters_tc:
                setattr(self, meter[0], self._get_handle(state_arg, 'meter', meter))
        if self.actuators_tc is not None:
            for actuator in self.actuators_tc:
                setattr(self, actuator[0], self._get_handle(state_arg, 'actuator', actuator))


    def _get_handle(self, state_arg, ems_type: str, ems_obj):
        try:
            handle = ""
            if ems_type is 'var':
                handle = self.api.get_variable_handle(state_arg,
                                                      ems_obj[1],  # var name
                                                      ems_obj[2])  # var key
            elif ems_type is 'int_var':
                handle = self.api.get_internal_variable_handle(state_arg,
                                                               ems_obj[1],  # int var name
                                                               ems_obj[2])  # int var key
            elif ems_type is 'meter':
                handle = self.api.get_meter_handle(state_arg,
                                                   ems_obj[1])  # meter name
            elif ems_type is "actuator":
                handle = self.api.get_internal_variable_handle(state_arg,
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


    def _update_ems_vals(self, state_arg):
        if self.vars_tc is not None:
            for var in self.vars_tc:
                data_i = self.api.get_variable_value(state_arg, getattr(self, var[0] + '_handle'))
                getattr(self, var[0] + '_data').append(data_i)
        if self.meters_tc is not None:
            for meter in self.meters_tc:
                data_i = self.api.get_meter_value(state_arg, getattr(self, meter[0] + '_handle'))
                getattr(self, meter[0] + '_data').append(data_i)
        if self.actuators_tc is not None:
            for actuator in self.actuators_tc:
                data_i = self.api.get_actuator_value(state_arg, getattr(self, actuator[0] + '_handle'))
                getattr(self, actuator[0] + '_data').append(data_i)
        # update static (internal) variables once
        if self.int_vars_tc is not None and not self.static_vars_gathered:
            for int_var in self.int_vars_tc:
                data_i = self.api.get_internal_variable_value(state_arg, getattr(self, int_var[0] + '_handle'))
                getattr(self, int_var[0] + '_data').append(data_i)
                self.static_vars_gathered = True


    def _update_weather_vals(self):
        # update and append present weather vals
        for weather_type in self.weather_tc:
            data_i = self._get_weather('today', weather_type, self.hours[-1], self.zone_ts)
            getattr(self, weather_type + '_data').append(data_i)


    def _get_weather(self, when: str, weather_type: str, hour:int, zone_ts: int):
        api = self.api
        state = self.state
        if when is 'today':
            weather_dict = {
                'sun_up': api.exchange.sun_is_up,
                'rain': api.exchange.today_weather_is_raining_at_time,
                'snow': api.exchange.today_weather_is_raning_at_time,
                'precipitation': api.exchange.today_weather_liquid_precipitation_at_time,
                'bar_pressure': api.exchange.today_weather_barometric_pressure_at_time,
                'dew_point': api.exchange.today_weather_outdoor_dew_point_at_time,
                'dry_bulb' : api.exchange.today_weather_outdoor_dry_buld_at_time,
                'rel_humidity': api.exchange.today_weather_outdoor_relative_humidity_at_time,
                'wind_dir': api.exchange.today_weather_wind_direction_at_time,
                'wind_speed': api.exchange.today_weather_wind_speed_at_time
                # TODO or use getattr(self, 'api.exchange.' + when + '_weather_..._at time') and eliminate if else
            }
        elif when is 'tomorrow':
            weather_dict = {
                # NO SUN
                'rain': api.exchange.tomorrow_weather_is_raining_at_time,
                'snow': api.exchange.tomorrow_weather_is_raning_at_time,
                'precipitation': api.exchange.tomorrow_weather_liquid_precipitation_at_time,
                'bar_pressure': api.exchange.tomorrow_weather_barometric_pressure_at_time,
                'dew_point': api.exchange.tomorrow_weather_outdoor_dew_point_at_time,
                'dry_bulb': api.exchange.tomorrow_weather_outdoor_dry_buld_at_time,
                'rel_humidity': api.exchange.tomorrow_weather_outdoor_relative_humidity_at_time,
                'wind_dir': api.exchange.tomorrow_weather_wind_direction_at_time,
                'wind_speed': api.exchange.tomorrow_weather_wind_speed_at_time
            }
        if weather_type is 'sun_up':  # today only
            return weather_dict.get('sun_up')(state)  # no timestep argument, current
        else:
            return weather_dict.get(weather_type)(state, hour, zone_ts)


    def set_calling_point(self, calling_pnt: str):


    def _callback_function(self, state_arg):
        # get handles once
        if not self.got_ems_handles:
            # verify ems objects are ready for access, skip until
            if not self.api.exchange.api_data_fully_ready(state_arg):
                return
            self._set_ems_handles(state_arg)
            self.got_ems_handles = True

        # prepare data dashboard plot
        self.ddash.init_ddash()

        # skip warmup
        if self.api.exchange.warmup_flag(state_arg):
            return

        # update & append simulation data
        self._update_time()
        self._update_ems_vals(state_arg)


    class EnergyPlusModel:

        def __init__(self):

    class DataDashboard:

        def __init__(self):

        def init_ddash(self):


    class BcaEnv:
        """ Inspired by OpenAI gym https://gym.openai.com/"""
        def __init__(self):

        def _get_observation(self):
            return observation

        def _get_reward(self):
            return reward

        def _take_action(self):

        def step_env(self):
            return observation, reward, done, info

        def reset_sim(self):


    #####################################
import emspy
ep_path = ''  # path to EnergyPlus download in filesystem
ep_file_path = ''  # path to .idf file for simulation
ep_idf_to_run = ep_file_path + ''  #
ep_weather_path = ep_path + '/WeatherData/.epw'

# define EMS sensors and actuators to be used via 'Table of Contents'
#vars_tc = [["attr_handle_name", "variable_type", "variable_key"],[...],...]
# int_vars_tc = [["attr_handle_name", "variable_type", "variable_key"],[...],...]
# meters_tc = [["attr_handle_name", "meter_name",[...],...]
# actuators_tc = [["attr_handle_name", "component_type", "control_type", "actuator_key"],[...],...]
# weather_tc = ["sun", "rain", "snow", "wind_dir", ...]

ems = EmsPy(ep_path, ep_idf_to_run, vars_tc, int_vars_tc, meters_tc, actuators_tc)
bca = ems.BcaEnv()





########################################################################################
#
#
# class Test(EnergyPlusPlugin):
#
#     def __init__(self):
#         super().__init__()
#
#         # class member variables
#         self.relhum_from_output_var_handle = None
#         self.relhum_from_actuator_var_handle = None
#         self.outdoor_air_relhum_handle = None
#         self.outdoor_air_relhum_actuator_handle = None
#         self.need_to_get_handles = True
#
#     def get_handles(self, state):
#         # get variable handles and save for later
#         self.outdoor_air_relhum_handle = self.api.exchange.get_variable_handle(state,
#                                                                                "Site Outdoor Air Relative Humidity",
#                                                                                "Environment")
#         self.outdoor_air_relhum_actuator_handle = self.api.exchange.get_actuator_handle(state,
#                                                                                         "Weather Data",
#                                                                                         "Outdoor Relative Humidity",
#                                                                                         "Environment")
#         self.relhum_from_output_var_handle = self.api.exchange.get_global_handle(state, "RelHumFromOutputVar")
#         self.relhum_from_actuator_var_handle = self.api.exchange.get_global_handle(state, "RelHumFromActuator")
#         self.need_to_get_handles = False
#
#     def on_begin_zone_timestep_before_set_current_weather(self, state) -> int:
#
#         # initialize if the API is ready
#         if self.need_to_get_handles:
#             if self.api.exchange.api_data_fully_ready(state):
#                 self.get_handles(state)
#             else:
#                 return 0
#
#         # get the current relative humidity value from the output variable, assign it to the global variable
#         current_relhum = self.api.exchange.get_variable_value(state, self.outdoor_air_relhum_handle)
#         self.api.exchange.set_global_value(state, self.relhum_from_output_var_handle, current_relhum)
#
#         # set the new ODA relhum value via the actuator and assign it to the global variable
#         new_relhum = 34.56789
#
#         self.api.exchange.set_actuator_value(state, self.outdoor_air_relhum_actuator_handle, new_relhum)
#         self.api.exchange.set_global_value(state, self.relhum_from_actuator_var_handle, new_relhum)
#         return 0
#
# import os
# import shutil
# import sys
# import datetime
#
# import matplotlib as mpl
# import matplotlib.pyplot as plt
# import numpy as np
# import pandas as pd
#
# import torch
# import openstudio  # ver 3.2.0 !pip list
#
# # work arouund
# os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
# # OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized.
#
# # insert the repo build tree or install path into the search Path, then import the EnergyPlus API
# ep_path = 'A:/Programs/EnergyPlusV9-5-0/'
# project_name = '/PyEMS_CJE/'
# project_path = 'A:/Files/PycharmProjects/RL-BCA/EnergyPlus-PythonAPI-Examples/api-example-copies' + project_name
#
# sys.path.insert(0, ep_path)
# from pyenergyplus.api import EnergyPlusAPI
# # import pyenergyplus
# # print(pyenergyplus.api.EnergyPlusAPI.api_version())  # 0.2
#
# ts = 5  # seconds
# step_freq = int(60/ts)  # num of steps per hour
#
# # ----------------------------------------OpenStudio Route--------------------------------------------------------------
#
# m = openstudio.model.exampleModel()  # {Model} idf file
# #
# # [x.remove() for x in m.getOutputVariables()]
# #
# # o = openstudio.model.OutputVariable("Site Outdoor Air Drybulb Temperature", m)  # {OpenStudioRuleset}
# # o.setKeyValue("Environment")
# # o.setReportingFrequency("Timestep")
# #
# # for var in ["Zone Mean Air Temperature",
# #             "Zone Thermostat Heating Setpoint Temperature",
# #             "Zone Thermostat Cooling Setpoint Temperature"]:
# #     o = openstudio.model.OutputVariable(var, m)
# #     #o.setKeyValue(openstudio.model.getThermalZones(m)[0].nameString())
# #     o.setReportingFrequency("Timestep")
# #
# #
# # [print(x) for x in m.getOutputVariables()]
# #
# # timestep = m.getTimestep()  # set from model
# # print(timestep)
# #
# # ## -------------------------------- Modifying OSM --------------------------------------------
# #
# # # SET # OF TIMESTEPS PER HOUR
# # timestep.setNumberOfTimestepsPerHour(step_freq)
# # print(timestep)
# #
# # z = m.getThermalZones()[0]
# # t = z.thermostatSetpointDualSetpoint().get()
# # heating_sch = t.heatingSetpointTemperatureSchedule().get()
# # o = heating_sch.to_ScheduleRuleset()
# # if o.is_initialized():
# #     heating_sch = o.get()
# #     print(heating_sch.briefDescription())
# # else:
# #     print(heating_sch.briefDescription())
# # #heating_sch = openstudio.model.toScheduleRuleset(heating_sch).get()
# #
# # print(heating_sch.defaultDaySchedule())
# #
# # [print(x) for x in heating_sch.scheduleRules()]
# #
# # r = m.getRunPeriod()  # {RunPeriod}
# # print(r)
# #
# # r.setEndMonth(1)
# # r.setEndDayOfMonth(20)
# #
# # print(r)
# #
# # # translate modified osm to idf
# # ft = openstudio.energyplus.ForwardTranslator()
# # w = ft.translateModel(m)
# # w.save(openstudio.path(project_path + 'test.idf'), True)
#
# ## -----------------------------------------Class------------------------------------------------------------------
#
#
# class TwoGraphs:
#     def __init__(self, filename_to_run, zone_name):
#
#         self.filename_to_run = filename_to_run
#         self.zone_name = zone_name
#
#         # Storing stuff
#         self.got_handles = False
#         self.oa_temp_handle = -1
#         self.zone_temp_handle = -1
#         self.zone_htg_tstat_handle = -1
#         self.zone_clg_tstat_handle = -1
#         self.zone_rh_handle = -1  # added by CJE
#         self.count = 0
#         self.plot_update_interval = 250  # time steps
#
#         self.x = []
#         self.y_outdoor = []
#         self.y_zone = []
#         self.y_htg = []
#         self.y_clg = []
#         self.y_overshoot = []
#         self.y_rh = []  # added by CJE
#         self.years = []
#         self.months = []
#         self.days = []
#         self.hours = []
#         self.minutes = []
#         self.current_times = []
#         self.actual_date_times = []
#         self.actual_times = []
#         self.df = pd.DataFrame({'OA Temp': [], 'Zone Temp': [], 'Htg Tstat': [], 'Clg Tstat': []})
#
#     def init_plot(self):
#
#         fig, (ax0, ax1) = plt.subplots(nrows=2, sharex=True, figsize=(8, 6),
#                                        gridspec_kw={'height_ratios': [2, 1]},
#                                        num='Two graphs')
#         h1, = ax0.plot([], [], label="Outdoor Air Temp")
#         h2, = ax0.plot([], [], label="Zone Temperature")
#         h_overshoot, = ax1.plot([], [], label="Overshoot")
#
#         ax0.set_ylabel('Temperature [C]')
#         ax0.legend(loc='lower right')
#         ax0.set_ylim(-25, 40)
#
#         ax1.set_title('Overshoot/undershoot compared to thermostat setpoint [C]')
#         ax1.set_xlabel('Zone time step index')
#         ax1.set_ylabel('Temperature difference [C]')
#         ax1.legend(loc='lower right')
#         ax1.set_ylim(-1.1, 1.1)
#         # plt.show(False)
#         # plt.draw()
#         fig.autofmt_xdate()
#
#         # Store attributes
#         self.fig = fig
#         self.ax0 = ax0
#         self.ax1 = ax1
#         self.h1 = h1
#         self.h2 = h2
#         self.h_overshoot = h_overshoot
#
#         fig.show()
#         fig.canvas.draw()
#
#     def update_line(self):
#
#         # hl.set_data(x, y_outdoor)
#         # h2.set_data(x, y_zone)
#
#         self.h1.set_xdata(self.df.index)
#         self.h1.set_ydata(self.df['OA Temp'])
#         self.h2.set_xdata(self.df.index)
#         self.h2.set_ydata(self.df['Zone Temp'])
#
#         y_overshoot = []
#         for i, zone_temp in enumerate(self.y_zone):
#             if zone_temp < self.y_htg[i]:
#                 y_overshoot.append(zone_temp - self.y_htg[i])
#             elif zone_temp > self.y_clg[i]:
#                 y_overshoot.append(zone_temp - self.y_clg[i])
#             else:
#                 y_overshoot.append(0.0)
#
#         self.h_overshoot.set_xdata(self.df.index)
#         self.h_overshoot.set_ydata(y_overshoot)
#
#         self.ax0.set_xlim(self.x[0], self.x[-1])
#         # self.ax1.set_ylim(min(y_overshoot), max(y_overshoot))
#         # ax.autoscale_view()
#         self.fig.canvas.draw()
#
#     def callback_function(self, state_argument):
#         # run only once first iter
#         if not self.got_handles:
#             if not api.exchange.api_data_fully_ready(state_argument):
#                 return
#             self.oa_temp_handle = (
#                 api.exchange.get_variable_handle(state_argument, u"SITE OUTDOOR AIR DRYBULB TEMPERATURE",
#                                                  u"ENVIRONMENT")
#             )
#             self.zone_temp_handle = (
#                 api.exchange.get_variable_handle(state_argument,
#                                                  "Zone Mean Air Temperature",
#                                                  self.zone_name)
#             )
#             self.zone_htg_tstat_handle = (
#                 api.exchange.get_variable_handle(state_argument,
#                                                  "Zone Thermostat Heating Setpoint Temperature",
#                                                  self.zone_name)
#             )
#             self.zone_clg_tstat_handle = (
#                 api.exchange.get_variable_handle(state_argument,
#                                                  "Zone Thermostat Cooling Setpoint Temperature",
#                                                  self.zone_name)
#             )
#             # CJE
#             self.zone_rh_handle = (
#                 api.exchange.get_variable_handle(state_argument,
#                                                  "Zone Air Relative Humidity",
#                                                  self.zone_name)
#             )
#
#             # # --- Actuator ---
#             # self.test_actuator_handle = (
#             #     api.exchange.get_actuator_handle(state_argument,
#             #                                      "Main Heating Volume Flow Rate",
#             #                                      "AirLoopHVAC:OutdoorAirSystem"
#             #
#             #                                      self.zone_name)
#
#             # QUIT program if invalid sensors
#             if -1 in [self.oa_temp_handle, self.zone_temp_handle,
#                       self.zone_htg_tstat_handle, self.zone_clg_tstat_handle, self.zone_rh_handle]:
#                 print("***Python: Invalid handles, check spelling and sensor/actuator availability")
#                 sys.exit(1)
#             self.got_handles = True
#             self.init_plot()  # prepare plot
#
#         # Skip warmup
#         if api.exchange.warmup_flag(state_argument):
#             return
#
#         self.count += 1
#
#         oa_temp = api.exchange.get_variable_value(state_argument,
#                                                   self.oa_temp_handle)
#         self.y_outdoor.append(oa_temp)
#         zone_temp = api.exchange.get_variable_value(state_argument,
#                                                     self.zone_temp_handle)
#         self.y_zone.append(zone_temp)
#
#         zone_htg_tstat = api.exchange.get_variable_value(state_argument,
#                                                          self.zone_htg_tstat_handle)
#         self.y_htg.append(zone_htg_tstat)
#
#         zone_clg_tstat = api.exchange.get_variable_value(state_argument,
#                                                          self.zone_clg_tstat_handle)
#         self.y_clg.append(zone_clg_tstat)
#
#         # CJE relative humidity
#         rh = api.exchange.get_variable_value(state_argument, self.zone_rh_handle)
#         self.y_rh.append(rh)
#
#         # timing
#         year = api.exchange.year(state)
#         month = api.exchange.month(state)
#         day = api.exchange.day_of_month(state)
#         hour = api.exchange.hour(state)
#         minute = api.exchange.minutes(state)
#         current_time = api.exchange.current_time(state)
#         actual_date_time = api.exchange.actual_date_time(state)
#         actual_time = api.exchange.actual_time(state)
#
#         # Year is bogus, seems to be reading the weather file year instead...
#         # So harcode it to 2009
#         year = 2009
#         self.years.append(year)
#         self.months.append(month)
#         self.days.append(day)
#         self.hours.append(hour)
#         self.minutes.append(minute)
#
#         self.current_times.append(current_time)
#         self.actual_date_times.append(actual_date_time)
#         self.actual_times.append(actual_time)
#
#         timedelta = datetime.timedelta()
#         if hour >= 24.0:
#             hour = 23.0
#             timedelta += datetime.timedelta(hours=1)
#         if minute >= 60.0:
#             minute = 59
#             timedelta += datetime.timedelta(minutes=1)
#
#         dt = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute)
#         dt += timedelta
#         self.x.append(dt)
#
#         if self.count % self.plot_update_interval == 0:
#             self.df = pd.DataFrame({'OA Temp': self.y_outdoor,
#                                     'Zone Temp': self.y_zone,
#                                     'Htg Tstat': self.y_htg,
#                                     'Clg Tstat': self.y_clg,
#                                     'Zone RH': self.y_rh,  # CJE
#                                     },
#                                    index=self.x)
#
#             self.update_line()
#
# api = EnergyPlusAPI()
# state = api.state_manager.new_state()
#
#
# filename_to_run = project_path + 'test_CJE_act.idf'
# g = TwoGraphs(filename_to_run=filename_to_run,
#               zone_name=openstudio.model.getThermalZones(m)[0].nameString())
#
# api.runtime.callback_begin_zone_timestep_after_init_heat_balance(state, g.callback_function)
# api.runtime.run_energyplus(state,
#     [
#         '-w', ep_path + '/WeatherData/USA_CO_Golden-NREL.724666_TMY3.epw',
#         '-d', 'out',
#         filename_to_run
#     ]
# )
#
# # If you need to call run_energyplus again, then reset the state first
# api.state_manager.reset_state(state)
# plt.show()
