import os
import matplotlib.pyplot as plt
import pandas as pd
import shutil

import openstudio  # ver 3.2.0 !pip list
from EmsPy import emspy

# work arouund # TODO find reference to error correction
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
# OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized.

ep_path = 'A:/Programs/EnergyPlusV9-5-0/'
idf_file = r'\in_modified_ppl_test.idf'
os_folder = r'A:\Files\PycharmProjects\RL-BCA\OpenStudio_Models\BEM_Custom\Base_People'
ep_idf_to_run = os_folder + idf_file
ep_weather_path = os_folder + r'\BEM_5z_Unitary_base_people\files\USA_NY_Buffalo.Niagara.Intl.AP.725280_TMY3.epw'
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
    'z0_ppl_sched_dummy': ['Schedule Value', 'OfficeSmall BLDG_OCC_SCH DUMMY'],  # occupancy dummy sched
    # EMS output
    'z0_ppl': ['Zone People Occupant Count', 'Core_ZN ZN'],
    'z1_ppl': ['Zone People Occupant Count', 'Perimeter_ZN_1 ZN'],
    'z2_ppl': ['Zone People Occupant Count', 'Perimeter_ZN_2 ZN'],
    'z3_ppl': ['Zone People Occupant Count', 'Perimeter_ZN_3 ZN'],
    'z4_ppl': ['Zone People Occupant Count', 'Perimeter_ZN_4 ZN'],
}
actuators_tc = {
    'ppl_sched': ['Schedule:Year', 'Schedule Value', 'OfficeSmall Bldg_Occ_Sch'],
    'ppl_cnt': ['People', 'Number of People', 'Core_Zn Zn Office WholeBuilding - Sm Office People']
}
weather_tc = {
}

timesteps = 6
# create calling point with actuation function
calling_point = 'callback_after_predictor_after_hvac_managers'  # system timestep
# calling_point = 'callback_end_system_timestep_after_hvac_reporting'  # HVAC iteration loop
# calling_point = 'callback_begin_zone_timestep_before_init_heat_balance'


class Agent:
    def __init__(self):
        pass

    def observe(self):
        pass

    def act(self):
        return {'ppl_cnt': 0.5}


# create building energy simulation obj
sim = emspy.BcaEnv(ep_path, ep_idf_to_run, timesteps, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc)
# create RL agent obj
agent = Agent()

sim.set_calling_point_and_callback_function(calling_point, None, agent.act, True, 1, 1)

# RUN
sim.run_env(ep_weather_path)
sim.reset_state()

dfs = sim.get_df()

