import os
import matplotlib.pyplot as plt
import pandas as pd
import shutil

import openstudio  # ver 3.2.0 !pip list
from EmsPy import emspy

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
# OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized.

ep_path = 'A:/Programs/EnergyPlusV9-5-0/'
idf_file = r'\rl_in.idf'
os_folder = r'A:\Files\PycharmProjects\RL-BCA\OpenStudio_Models\BEM_EmsPy_Debug'
ep_idf_to_run = os_folder + idf_file
ep_weather_path = os_folder + r'\BEM_5z_Unitary_base_rl\files\USA_NY_Buffalo.Niagara.Intl.AP.725280_TMY3.epw'
cvs_output_path = ''

# --- create EMS Table of Contents (TC) for sensors/actuators ---

# vars_tc = {"attr_handle_name": ["variable_type", "variable_key"],...}
# int_vars_tc = {"attr_handle_name": "variable_type", "variable_key"],...}
# meters_tc = {"attr_handle_name": "meter_name",...}
# actuators_tc = {"attr_handle_name": ["component_type", "control_type", "actuator_key"],...}
# weather_tc = {"attr_name": "weather_metric",...}

int_vars_tc = {
}
meters_tc = {
}
vars_tc = {
    # people count
    'z1_ppl': ['Zone People Occupant Count', 'Perimeter_ZN_1 ZN'],

}
actuators_tc = {
    # HVAC control setpoints
    'zn1_cooling_sp': ['Zone Temperature Control', 'Cooling Setpoint', 'Perimeter_Zn_1 Zn'],
    'zn1_heating_sp': ['Zone Temperature Control', 'Heating Setpoint', 'Perimeter_Zn_1 Zn'],
    # setpoint tracking
    'zn1_cooling_sp_tracker': ['Schedule:Constant', 'Schedule Value', 'Cooling Setpoint Tracker'],
    'zn1_heating_sp_tracker': ['Schedule:Constant', 'Schedule Value', 'Heating Setpoint Tracker'],
    # reward tracking
    'reward': ['Schedule:Constant', 'Schedule Value', 'Reward Tracker'],
    # DView arbitrary data schedule tracking
}
weather_tc = {
    'oa_rh': 'outdoor_relative_humidity',
    'oa_db': 'outdoor_dry_bulb',
    'sun_up': 'sun_is_up',
    'raining': 'is_raining',
    'snowing': 'is_snowing'
}

# simulation params
timesteps = 6
cp = 'callback_begin_zone_timestep_before_init_heat_balance'

# create building energy simulation obj
sim = emspy.BcaEnv(ep_path, ep_idf_to_run, timesteps, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc)


# create RL agent obj
class Agent:
    def __init__(self):
        self.reward = 0

    def observe(self):
        return self.reward

    def act(self):
        return {
            'reward': self.reward,
            'zn1_cooling_sp': 23.889,  # 75f
            'zn1_heating_sp': 18.333,  # 65f
            'zn1_cooling_sp_tracker': 75,  # 75f  DView does not convert
            'zn1_heating_sp_tracker': 65,  # 65f
            }


# create agent object for tracking RL data
agent = Agent()

# establish calling points and callback functions
sim.set_calling_point_and_callback_function(cp, agent.observe, agent.act, True, 1, 1)

# RUN simulation
sim.run_env(ep_weather_path)
sim.reset_state()

dfs = sim.get_df()
# dfs = sim.get_df(to_csv_file=cvs_output_path)
