import os
import matplotlib.pyplot as plt
import pandas as pd
import shutil

import openstudio  # ver 3.2.0 !pip list
from EmsPy import emspy

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
# OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized.

ep_path = 'A:/Programs/EnergyPlusV9-5-0/'
idf_file = r'\in.idf'
os_folder = r'A:\Files\PycharmProjects\RL-BCA\OpenStudio_Models\BEM_EmsPy_Debug'
ep_idf_to_run = os_folder + idf_file
ep_weather_path = os_folder + r'\BEM_5z_Unitary_base_debug\files\USA_NY_Buffalo.Niagara.Intl.AP.725280_TMY3.epw'
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
    'z0_ppl_sched': ['Schedule Value', 'OfficeSmall BLDG_OCC_SCH'],
    # EMS output
    'z0_ppl': ['Zone People Occupant Count', 'Core_ZN ZN'],
    'z1_ppl': ['Zone People Occupant Count', 'Perimeter_ZN_1 ZN'],
    'z2_ppl': ['Zone People Occupant Count', 'Perimeter_ZN_2 ZN'],
    'z3_ppl': ['Zone People Occupant Count', 'Perimeter_ZN_3 ZN'],
    'z4_ppl': ['Zone People Occupant Count', 'Perimeter_ZN_4 ZN'],
}
actuators_tc = {
    'ppl_sched': ['Schedule:Constant', 'Schedule Value', 'People Const Sched'],
}
weather_tc = {
    'sun_up': 'sun_is_up',
    'raining': 'is_raining'
}

timesteps = 6
# create calling point with actuation function
cp1 = 'callback_begin_zone_timestep_before_init_heat_balance'
cp2 = 'callback_after_predictor_after_hvac_managers'  # system timestep
# cp3 = 'callback_end_system_timestep_after_hvac_reporting'  # HVAC iteration loop


# create building energy simulation obj
sim = emspy.BcaEnv(ep_path, ep_idf_to_run, timesteps, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc)
# create RL agent obj


class Agent:
    def __init__(self):
        self.ppl_sched = 0
        self.ppl_sched_after = 0
        pass

    def observe1(self):
        self.ppl_sched = sim.get_ems_data('z0_ppl_sched_dummy')
        # print(f'* PPL Sched: {self.ppl_sched}')

    def observe2(self):
        self.ppl_sched_after = sim.get_ems_data('z0_ppl')
        # print(f'  PPL Update: {self.ppl_sched_after}')

    def act(self):
        # print(f'  PPL Actuate: {self.ppl_sched}*')
        return {'ppl_sched': self.ppl_sched}


agent = Agent()

sim.set_calling_point_and_callback_function(cp1, None, None, True, 1, 1)
sim.set_calling_point_and_callback_function(cp2, agent.observe1, agent.act, True, 1, 1)
# sim.set_calling_point_and_callback_function(calling_point1, agent.observe2, None, True, 1, 1)

# sim.init_custom_dataframe_dict('custom_df', calling_point, 1, ['ppl_sched'])  # actuator lag

# RUN
sim.run_env(ep_weather_path)
sim.reset_state()

dfs = sim.get_df()
# dfs = sim.get_df(to_csv_file=cvs_output_path)

# move out folder to openstudio folder
# shutil.move('out', os_folder + '5office_small_ems' + '/out')





