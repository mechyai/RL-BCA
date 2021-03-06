import os
import matplotlib.pyplot as plt
import pandas as pd

import openstudio  # ver 3.2.0 !pip list

from EmsPy import emspy

# work arouund # TODO find reference to
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
# OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized.

# insert the repo build tree or install path into the search Path, then import the EnergyPlus API
ep_path = 'A:/Programs/EnergyPlusV9-5-0/'
project_name = '/ModelRunTests/small_office_tests/'
project_path = 'A:/Files/PycharmProjects/RL-BCA' + project_name

# ep_file_path = ''  # path to .idf file for simulation
ep_idf_to_run = project_path + 'RefBldgSmallOfficeNew2004_v1.3_5.0_6A_USA_MN_MINNEAPOLIS.idf'
ep_weather_path = '/Resource_Files/reference_weather/6A_USA_MN_MINNEAPOLIS_TMY2.epw'

# TODO update to dict usage
# define EMS sensors and actuators to be used via 'Table of Contents'
# vars_tc = {"attr_handle_name": ["variable_type", "variable_key"],...}
# int_vars_tc = {"attr_handle_name": "variable_type", "variable_key"],...}
# meters_tc = {"attr_handle_name": "meter_name",...}
# actuators_tc = {"attr_handle_name": ["component_type", "control_type", "actuator_key"],...}
# weather_tc = {"attr_name": "weather_metric",...}

# create EMS Table of Contents (TC)
zone = 'Thermal Zone 1'
vars_tc = {'oa_temp': ['site outdoor air drybulb temperature', 'environment'],
           'zone_temp': ['zone mean air temperature', zone]}

int_vars_tc = None
meters_tc = None
# still not working
actuators_tc = {'act_odb_temp': ['weather data', 'outdoor dry bulb', 'environment']}
weather_tc = {'sun': 'sun_is_up', 'rain': 'is_raining', 'wind_dir': 'wind_direction',
              'out_rh': 'outdoor_relative_humidity'}

# create calling point with actuation function and required callback fxn arguments
calling_point = 'callback_begin_zone_timestep_after_init_heat_balance'

ts = 12

# agent = emspy.BcaEnv(ep_path, ep_idf_to_run, ts, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc)
agent = emspy.BcaEnv(ep_path, ep_idf_to_run, ts, None, None, None, None, None)

class test_class:
    def __init__(self):
        self.param_data = 0


agent_params = test_class()


def actuation_fxn1():
    agent_params.param_data += 1
    print(agent_params.param_data)
    data = agent.get_ems_data(['wind_dir'], [0, 1, 2])
    print(f'Data: {data}')
    return None


# agent.set_calling_point_and_actuation_function(calling_point, actuation_fxn1, False, 1, 1)
# agent.set_calling_point_and_actuation_function(None, None, False)

# create custom dict
# agent.init_custom_dataframe_dict('df1', calling_point, 4, ['act_odb_temp', 'sun'])
# agent.init_custom_dataframe_dict('df2', calling_point, 2, ['rain', 'zone_temp'])

agent.run_env(ep_weather_path)
# agent.reset_state()

