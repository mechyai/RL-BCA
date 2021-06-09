import os
import matplotlib.pyplot as plt
import pandas as pd

import openstudio  # ver 3.2.0 !pip list

import emspy

# work arouund # TODO find reference to
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
# vars_tc = [["attr_handle_name", "variable_type", "variable_key"],[...],...]
# int_vars_tc = [["attr_handle_name", "variable_type", "variable_key"],[...],...]
# meters_tc = [["attr_handle_name", "meter_name",[...],...]
# actuators_tc = [["attr_handle_name", "component_type", "control_type", "actuator_key"],[...],...]
# weather_tc = ["sun", "rain", "snow", "wind_dir", ...]

# create EMS Table of Contents (TC)
zone = 'Thermal Zone 1'
vars_tc = [['oa_temp', 'site outdoor air drybulb temperature', 'environment'],
           ['zone_temp', 'zone mean air temperature', zone]]
int_vars_tc = None
meters_tc = None
# still not working
actuators_tc = [['act_odb_temp', 'weather data', 'outdoor dry bulb', 'environment']]
weather_tc = ['sun_is_up', 'is_raining', 'wind_direction', 'outdoor_relative_humidity']

# create calling point with actuation function and required callback fxn arguments
calling_point = 'callback_begin_zone_timestep_after_init_heat_balance'


def actuation_fxn1(agent):
    # data = 1
    data = agent.get_ems_data(['oa_temp'], [0, 1, 2])
    print(f'working...{data}')
    return None


# {'calling_point': [actuation_fxn, update state, update state freq, update act freq],...}
cp_dict = {calling_point: [actuation_fxn1, True, 1, 1]}
ts = 12

agent = emspy.BcaEnv(ep_path, ep_idf_to_run, ts, cp_dict, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc)

# create custom dict
agent.init_custom_dataframe_dict('df1', calling_point, 4, ['act_odb_temp', 'sun_is_up'])
agent.init_custom_dataframe_dict('df2', calling_point, 2, ['is_raining', 'zone_temp'])

agent.run_env(ep_weather_path)
# agent.run_env(ep_weather_path)
agent.reset_state()

