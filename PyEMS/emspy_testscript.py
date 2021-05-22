import os
import matplotlib.pyplot as plt
import pandas as pd

import openstudio  # ver 3.2.0 !pip list

import emspy


# work arouund
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
# OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized.

# insert the repo build tree or install path into the search Path, then import the EnergyPlus API
ep_path = 'A:/Programs/EnergyPlusV9-5-0/'
project_name = '/PyEMS/'
project_path = 'A:/Files/PycharmProjects/RL-BCA' + project_name

# ep_file_path = ''  # path to .idf file for simulation
ep_idf_to_run = project_path + 'test_CJE_act.idf'
ep_weather_path = ep_path + '/WeatherData/USA_CO_Golden-NREL.724666_TMY3.epw'

# define EMS sensors and actuators to be used via 'Table of Contents'
#vars_tc = [["attr_handle_name", "variable_type", "variable_key"],[...],...]
# int_vars_tc = [["attr_handle_name", "variable_type", "variable_key"],[...],...]
# meters_tc = [["attr_handle_name", "meter_name",[...],...]
# actuators_tc = [["attr_handle_name", "component_type", "control_type", "actuator_key"],[...],...]
# weather_tc = ["sun", "rain", "snow", "wind_dir", ...]

zone = 'Thermal Zone 1'
vars_tc = [['oa_temp', 'site outdoor air drybulb temperature', 'environment'],
           ['zone_temp', 'zone mean air temperature', zone]]
int_vars_tc = None
meters_tc = None
# still not working
actuators_tc = [['act_odb_temp', 'weather data', 'outdoor dry bulb', 'environment']]
weather_tc = ['sun_is_up', 'is_raining', 'wind_direction', 'outdoor_relative_humidity']


# ems = emspy.EmsPy(ep_path, ep_idf_to_run, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc)
calling_point = 'callback_begin_zone_timestep_after_init_heat_balance'
#ems._run_simulation(ep_weather_path, calling_point)
ts = 12
emspy.EmsPy.ep_path = ep_path
agent = emspy.BcaEnv(ep_path, ep_idf_to_run, ts, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc)
agent.reset_sim(ep_weather_path, calling_point)

# ems._reset_state()








class TwoGraphs:
    def __init__(self, filename_to_run, zone_name):

        self.zone_name = zone_name

        self.plot_update_interval = 250  # time steps TODO

        self.df = pd.DataFrame({'OA Temp': [], 'Zone Temp': [], 'Htg Tstat': [], 'Clg Tstat': []})  # TODO

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

    def get_handle(self, state_argument):
        self.oa_temp_handle = (
            api.exchange.get_variable_handle(state_argument, u"SITE OUTDOOR AIR DRYBULB TEMPERATURE",
                                             u"ENVIRONMENT")
        )

    def callback_function(self, state_argument):
        # run only once first iter
        if not self.got_handles:
            if not api.exchange.api_data_fully_ready(state_argument):
                return

            self.get_handle(state_argument)

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

            # ---------------------------------------- Actuator TEST ----------------------------------------
            # < EnergyManagementSystem: Actuator Available >, Component Unique Name, Component Type, Control Type, Units
            # EnergyManagementSystem: Actuator Available, THERMAL ZONE 1, Zone Temperature Control, Cooling Setpoint,[C]
            # self.test_actuator_handle = (
            #     api.exchange.get_actuator_handle(state_argument,
            #                                      "component type / actuator category",
            #                                      "control type / name",
            #                                      "actuator key / instance")
            # )
            self.test_actuator_handle = (
                api.exchange.get_actuator_handle(state_argument,
                                                 "Zone Temperature Control",
                                                 "Cooling Setpoint",
                                                 "Thermal Zone 1")
            )
            # self.test_weather_handle = (
            #     api.exchange.get_actuator_handle(state_argument,
            #                                      "Weather Data",
            #                                      "Outdoor Dry Bulb",
            #                                      "Environment")
            # )

            print('*** test actuator handle: ' + str(self.test_actuator_handle))
            # print('*** test weather handle: ' + str(self.test_weather_handle))


        ## ** set actuator arbitrary
        value = api.exchange.get_actuator_value(state_argument, self.test_actuator_handle)
        # print("***actuator value:" + str(value))
        api.exchange.set_actuator_value(state_argument, self.test_actuator_handle, 10000)

        oa_temp = api.exchange.get_variable_value(state,
                                                  self.oa_temp_handle)
        self.y_outdoor.append(oa_temp)
        zone_temp = api.exchange.get_variable_value(state,
                                                    self.zone_temp_handle)
        self.y_zone.append(zone_temp)

        zone_htg_tstat = api.exchange.get_variable_value(state,
                                                         self.zone_htg_tstat_handle)
        self.y_htg.append(zone_htg_tstat)

        zone_clg_tstat = api.exchange.get_variable_value(state,
                                                         self.zone_clg_tstat_handle)
        self.y_clg.append(zone_clg_tstat)

        # CJE relative humidity
        rh = api.exchange.get_variable_value(state_argument, self.zone_rh_handle)
        self.y_rh.append(rh)


