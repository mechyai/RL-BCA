#!
# code inspired by https://gist.github.com/mitchute/5a9f107aba213f1b683f4052027fc162
#!

class EmsPy:

    def __init__(self, ep_idf_to_run):
        from pyenergyplus.api import EnergyPlusAPI
        self.api = EnergyPlusAPI()  # instantiation of Python EMS API
        self.bca = BcaEnv()
        self.ddashboard = DataDashboard()

        self.ep_idf = ep_idf_to_run  # E+ idf file to simulation

        self.got_var_handles = False
        self.got_internal_handles = False
        self.got_actuator_handles = False


    def get_var_handles(self, state_arg):
        self.got_var_handles = True

    def get_internal_handles(self, state_arg, internal_vars):
        self.got_internal_handles = True
        for i in internal_vars:
            var_name = internal_vars[0]

    def get_actuator_handles(self, state_arg):
        self.got_actuator_handles = True

    def callback_function(self, state_arg):
        # run only once initially
        if not self.got_handles:
            if not self.api.exhanch.api_data_fully_ready(state_arg):
                return
            # get EMS sensor and actuator handles from sim
            self.get_var_handles(state_arg)
            self.get_internal_handles(state_arg)
            self.get_actuator_handles(state_arg)

    def calling_point(self, calling_pnt: str):

class DataDashboard:
    def __init__(self):

    def init_plot(self):


class BcaEnv:
    """ Inspired by OpenAI gym https://gym.openai.com/"""
    def __init__(self):

    def get_observation(self):
        return observation

    def get_reward(self):
        return reward

    def take_action(self):

    def reset_sim(self):


#####################################

ep_path = ''  # path to EnergyPlus download in filesystem
ep_file_path = ''  # path to .idf file for simulation
ep_idf_to_run = ep_file_path + ''  #
ep_weather_path = ep_path + '/WeatherData/.epw'

ems = EmsPy()
ems.get_var_handles()
ems.get_internal_handles()
ems.get_actuator_handles()








class Test(EnergyPlusPlugin):

    def __init__(self):
        super().__init__()

        # class member variables
        self.relhum_from_output_var_handle = None
        self.relhum_from_actuator_var_handle = None
        self.outdoor_air_relhum_handle = None
        self.outdoor_air_relhum_actuator_handle = None
        self.need_to_get_handles = True

    def get_handles(self, state):
        # get variable handles and save for later
        self.outdoor_air_relhum_handle = self.api.exchange.get_variable_handle(state,
                                                                               "Site Outdoor Air Relative Humidity",
                                                                               "Environment")
        self.outdoor_air_relhum_actuator_handle = self.api.exchange.get_actuator_handle(state,
                                                                                        "Weather Data",
                                                                                        "Outdoor Relative Humidity",
                                                                                        "Environment")
        self.relhum_from_output_var_handle = self.api.exchange.get_global_handle(state, "RelHumFromOutputVar")
        self.relhum_from_actuator_var_handle = self.api.exchange.get_global_handle(state, "RelHumFromActuator")
        self.need_to_get_handles = False

    def on_begin_zone_timestep_before_set_current_weather(self, state) -> int:

        # initialize if the API is ready
        if self.need_to_get_handles:
            if self.api.exchange.api_data_fully_ready(state):
                self.get_handles(state)
            else:
                return 0

        # get the current relative humidity value from the output variable, assign it to the global variable
        current_relhum = self.api.exchange.get_variable_value(state, self.outdoor_air_relhum_handle)
        self.api.exchange.set_global_value(state, self.relhum_from_output_var_handle, current_relhum)

        # set the new ODA relhum value via the actuator and assign it to the global variable
        new_relhum = 34.56789

        self.api.exchange.set_actuator_value(state, self.outdoor_air_relhum_actuator_handle, new_relhum)
        self.api.exchange.set_global_value(state, self.relhum_from_actuator_var_handle, new_relhum)
        return 0

import os
import shutil
import sys
import datetime

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import torch
import openstudio  # ver 3.2.0 !pip list

# work arouund
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
# OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized.

# insert the repo build tree or install path into the search Path, then import the EnergyPlus API
ep_path = 'A:/Programs/EnergyPlusV9-5-0/'
project_name = '/PyEMS_CJE/'
project_path = 'A:/Files/PycharmProjects/RL-BCA/EnergyPlus-PythonAPI-Examples/api-example-copies' + project_name

sys.path.insert(0, ep_path)
from pyenergyplus.api import EnergyPlusAPI
# import pyenergyplus
# print(pyenergyplus.api.EnergyPlusAPI.api_version())  # 0.2

ts = 5  # seconds
step_freq = int(60/ts)  # num of steps per hour

# ----------------------------------------OpenStudio Route--------------------------------------------------------------

m = openstudio.model.exampleModel()  # {Model} idf file
#
# [x.remove() for x in m.getOutputVariables()]
#
# o = openstudio.model.OutputVariable("Site Outdoor Air Drybulb Temperature", m)  # {OpenStudioRuleset}
# o.setKeyValue("Environment")
# o.setReportingFrequency("Timestep")
#
# for var in ["Zone Mean Air Temperature",
#             "Zone Thermostat Heating Setpoint Temperature",
#             "Zone Thermostat Cooling Setpoint Temperature"]:
#     o = openstudio.model.OutputVariable(var, m)
#     #o.setKeyValue(openstudio.model.getThermalZones(m)[0].nameString())
#     o.setReportingFrequency("Timestep")
#
#
# [print(x) for x in m.getOutputVariables()]
#
# timestep = m.getTimestep()  # set from model
# print(timestep)
#
# ## -------------------------------- Modifying OSM --------------------------------------------
#
# # SET # OF TIMESTEPS PER HOUR
# timestep.setNumberOfTimestepsPerHour(step_freq)
# print(timestep)
#
# z = m.getThermalZones()[0]
# t = z.thermostatSetpointDualSetpoint().get()
# heating_sch = t.heatingSetpointTemperatureSchedule().get()
# o = heating_sch.to_ScheduleRuleset()
# if o.is_initialized():
#     heating_sch = o.get()
#     print(heating_sch.briefDescription())
# else:
#     print(heating_sch.briefDescription())
# #heating_sch = openstudio.model.toScheduleRuleset(heating_sch).get()
#
# print(heating_sch.defaultDaySchedule())
#
# [print(x) for x in heating_sch.scheduleRules()]
#
# r = m.getRunPeriod()  # {RunPeriod}
# print(r)
#
# r.setEndMonth(1)
# r.setEndDayOfMonth(20)
#
# print(r)
#
# # translate modified osm to idf
# ft = openstudio.energyplus.ForwardTranslator()
# w = ft.translateModel(m)
# w.save(openstudio.path(project_path + 'test.idf'), True)

## -----------------------------------------Class------------------------------------------------------------------


class TwoGraphs:
    def __init__(self, filename_to_run, zone_name):

        self.filename_to_run = filename_to_run
        self.zone_name = zone_name

        # Storing stuff
        self.got_handles = False
        self.oa_temp_handle = -1
        self.zone_temp_handle = -1
        self.zone_htg_tstat_handle = -1
        self.zone_clg_tstat_handle = -1
        self.zone_rh_handle = -1  # added by CJE
        self.count = 0
        self.plot_update_interval = 250  # time steps

        self.x = []
        self.y_outdoor = []
        self.y_zone = []
        self.y_htg = []
        self.y_clg = []
        self.y_overshoot = []
        self.y_rh = []  # added by CJE
        self.years = []
        self.months = []
        self.days = []
        self.hours = []
        self.minutes = []
        self.current_times = []
        self.actual_date_times = []
        self.actual_times = []
        self.df = pd.DataFrame({'OA Temp': [], 'Zone Temp': [], 'Htg Tstat': [], 'Clg Tstat': []})

    def init_plot(self):

        fig, (ax0, ax1) = plt.subplots(nrows=2, sharex=True, figsize=(8, 6),
                                       gridspec_kw={'height_ratios': [2, 1]},
                                       num='Two graphs')
        h1, = ax0.plot([], [], label="Outdoor Air Temp")
        h2, = ax0.plot([], [], label="Zone Temperature")
        h_overshoot, = ax1.plot([], [], label="Overshoot")

        ax0.set_ylabel('Temperature [C]')
        ax0.legend(loc='lower right')
        ax0.set_ylim(-25, 40)

        ax1.set_title('Overshoot/undershoot compared to thermostat setpoint [C]')
        ax1.set_xlabel('Zone time step index')
        ax1.set_ylabel('Temperature difference [C]')
        ax1.legend(loc='lower right')
        ax1.set_ylim(-1.1, 1.1)
        # plt.show(False)
        # plt.draw()
        fig.autofmt_xdate()

        # Store attributes
        self.fig = fig
        self.ax0 = ax0
        self.ax1 = ax1
        self.h1 = h1
        self.h2 = h2
        self.h_overshoot = h_overshoot

        fig.show()
        fig.canvas.draw()

    def update_line(self):

        # hl.set_data(x, y_outdoor)
        # h2.set_data(x, y_zone)

        self.h1.set_xdata(self.df.index)
        self.h1.set_ydata(self.df['OA Temp'])
        self.h2.set_xdata(self.df.index)
        self.h2.set_ydata(self.df['Zone Temp'])

        y_overshoot = []
        for i, zone_temp in enumerate(self.y_zone):
            if zone_temp < self.y_htg[i]:
                y_overshoot.append(zone_temp - self.y_htg[i])
            elif zone_temp > self.y_clg[i]:
                y_overshoot.append(zone_temp - self.y_clg[i])
            else:
                y_overshoot.append(0.0)

        self.h_overshoot.set_xdata(self.df.index)
        self.h_overshoot.set_ydata(y_overshoot)

        self.ax0.set_xlim(self.x[0], self.x[-1])
        # self.ax1.set_ylim(min(y_overshoot), max(y_overshoot))
        # ax.autoscale_view()
        self.fig.canvas.draw()

    def callback_function(self, state_argument):
        # run only once first iter
        if not self.got_handles:
            if not api.exchange.api_data_fully_ready(state_argument):
                return
            self.oa_temp_handle = (
                api.exchange.get_variable_handle(state_argument, u"SITE OUTDOOR AIR DRYBULB TEMPERATURE",
                                                 u"ENVIRONMENT")
            )
            self.zone_temp_handle = (
                api.exchange.get_variable_handle(state_argument,
                                                 "Zone Mean Air Temperature",
                                                 self.zone_name)
            )
            self.zone_htg_tstat_handle = (
                api.exchange.get_variable_handle(state_argument,
                                                 "Zone Thermostat Heating Setpoint Temperature",
                                                 self.zone_name)
            )
            self.zone_clg_tstat_handle = (
                api.exchange.get_variable_handle(state_argument,
                                                 "Zone Thermostat Cooling Setpoint Temperature",
                                                 self.zone_name)
            )
            # CJE
            self.zone_rh_handle = (
                api.exchange.get_variable_handle(state_argument,
                                                 "Zone Air Relative Humidity",
                                                 self.zone_name)
            )

            # # --- Actuator ---
            # self.test_actuator_handle = (
            #     api.exchange.get_actuator_handle(state_argument,
            #                                      "Main Heating Volume Flow Rate",
            #                                      "AirLoopHVAC:OutdoorAirSystem"
            #
            #                                      self.zone_name)

            # QUIT program if invalid sensors
            if -1 in [self.oa_temp_handle, self.zone_temp_handle,
                      self.zone_htg_tstat_handle, self.zone_clg_tstat_handle, self.zone_rh_handle]:
                print("***Python: Invalid handles, check spelling and sensor/actuator availability")
                sys.exit(1)
            self.got_handles = True
            self.init_plot()  # prepare plot

        # Skip warmup
        if api.exchange.warmup_flag(state_argument):
            return

        self.count += 1

        oa_temp = api.exchange.get_variable_value(state_argument,
                                                  self.oa_temp_handle)
        self.y_outdoor.append(oa_temp)
        zone_temp = api.exchange.get_variable_value(state_argument,
                                                    self.zone_temp_handle)
        self.y_zone.append(zone_temp)

        zone_htg_tstat = api.exchange.get_variable_value(state_argument,
                                                         self.zone_htg_tstat_handle)
        self.y_htg.append(zone_htg_tstat)

        zone_clg_tstat = api.exchange.get_variable_value(state_argument,
                                                         self.zone_clg_tstat_handle)
        self.y_clg.append(zone_clg_tstat)

        # CJE relative humidity
        rh = api.exchange.get_variable_value(state_argument, self.zone_rh_handle)
        self.y_rh.append(rh)

        # timing
        year = api.exchange.year(state)
        month = api.exchange.month(state)
        day = api.exchange.day_of_month(state)
        hour = api.exchange.hour(state)
        minute = api.exchange.minutes(state)
        current_time = api.exchange.current_time(state)
        actual_date_time = api.exchange.actual_date_time(state)
        actual_time = api.exchange.actual_time(state)

        # Year is bogus, seems to be reading the weather file year instead...
        # So harcode it to 2009
        year = 2009
        self.years.append(year)
        self.months.append(month)
        self.days.append(day)
        self.hours.append(hour)
        self.minutes.append(minute)

        self.current_times.append(current_time)
        self.actual_date_times.append(actual_date_time)
        self.actual_times.append(actual_time)

        timedelta = datetime.timedelta()
        if hour >= 24.0:
            hour = 23.0
            timedelta += datetime.timedelta(hours=1)
        if minute >= 60.0:
            minute = 59
            timedelta += datetime.timedelta(minutes=1)

        dt = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute)
        dt += timedelta
        self.x.append(dt)

        if self.count % self.plot_update_interval == 0:
            self.df = pd.DataFrame({'OA Temp': self.y_outdoor,
                                    'Zone Temp': self.y_zone,
                                    'Htg Tstat': self.y_htg,
                                    'Clg Tstat': self.y_clg,
                                    'Zone RH': self.y_rh,  # CJE
                                    },
                                   index=self.x)

            self.update_line()

api = EnergyPlusAPI()
state = api.state_manager.new_state()


filename_to_run = project_path + 'test_CJE_act.idf'
g = TwoGraphs(filename_to_run=filename_to_run,
              zone_name=openstudio.model.getThermalZones(m)[0].nameString())

api.runtime.callback_begin_zone_timestep_after_init_heat_balance(state, g.callback_function)
api.runtime.run_energyplus(state,
    [
        '-w', ep_path + '/WeatherData/USA_CO_Golden-NREL.724666_TMY3.epw',
        '-d', 'out',
        filename_to_run
    ]
)

# If you need to call run_energyplus again, then reset the state first
api.state_manager.reset_state(state)
plt.show()
