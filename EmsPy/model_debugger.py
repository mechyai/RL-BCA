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
idf_file = 'ems_base'
os_folder = 'A:\Files\PycharmProjects\RL-BCA\OpenStudio_Models'
ep_idf_to_run = os_folder + '/Test_Unitary/idf_files/' + idf_file + '.idf'
ep_weather_path = r'A:\Files\PycharmProjects\RL-BCA\Resource_Files\reference_weather\5A_USA_IL_CHICAGO-OHARE_TMY2.epw'
cvs_output_path = 'Test_DFs/' + idf_file + '_control_df'

# --- create EMS Table of Contents (TC) for sensors/actuators ---
# vars_tc = {"attr_handle_name": ["variable_type", "variable_key"],...}
# int_vars_tc = {"attr_handle_name": "variable_type", "variable_key"],...}
# meters_tc = {"attr_handle_name": "meter_name",...}
# actuators_tc = {"attr_handle_name": ["component_type", "control_type", "actuator_key"],...}
# weather_tc = {"attr_name": "weather_metric",...}
int_vars_tc = None
meters_tc = {
    'z0_e_hr': 'Electricity:Zone:CORE_ZN ZN',
    'z0_hvac_electricity': 'z0_hvac_electricity'
}
vars_tc = {
    # zones temps
    'z0_temp': ['Zone Air Temperature', 'Core_ZN ZN'],
    'z1_temp': ['Zone Air Temperature', 'Perimeter_ZN_1 ZN'],
    'z2_temp': ['Zone Air Temperature', 'Perimeter_ZN_2 ZN'],
    'z3_temp': ['Zone Air Temperature', 'Perimeter_ZN_3 ZN'],
    'z4_temp': ['Zone Air Temperature', 'Perimeter_ZN_4 ZN'],
    'z0_rh': ['Zone Air Relative Humidity', 'Core_ZN ZN'],
    # zones %rh
    'z1_rh': ['Zone Air Relative Humidity', 'Perimeter_ZN_1 ZN'],
    'z2_rh': ['Zone Air Relative Humidity', 'Perimeter_ZN_2 ZN'],
    'z3_rh': ['Zone Air Relative Humidity', 'Perimeter_ZN_3 ZN'],
    'z4_rh': ['Zone Air Relative Humidity', 'Perimeter_ZN_4 ZN'],
    # people count
    # 'z0_ppl': ['Zone People Occupant Count', 'Core_ZN ZN'],
    # 'z1_ppl': ['Zone People Occupant Count', 'Perimeter_ZN_1 ZN'],
    # 'z2_ppl': ['Zone People Occupant Count', 'Perimeter_ZN_2 ZN'],
    # 'z3_ppl': ['Zone People Occupant Count', 'Perimeter_ZN_3 ZN'],
    # 'z4_ppl': ['Zone People Occupant Count', 'Perimeter_ZN_4 ZN'],
    # # energy
    # 'z0_e': ['Unitary System Electricity Energy', 'Core_ZN ZN'],
    # 'z1_e': ['Unitary System Electricity Energy', 'Perimeter_ZN_1 ZN'],
    # 'z2_e': ['Unitary System Electricity Energy', 'Perimeter_ZN_2 ZN'],
    # 'z3_e': ['Unitary System Electricity Energy', 'Perimeter_ZN_3 ZN'],
    # 'z4_e': ['Unitary System Electricity Energy', 'Perimeter_ZN_4 ZN'],
    # # energy rate
    # 'z0_e_rate': ['Unitary System Electricity Rate', 'Core_ZN ZN'],
    # 'z1_e_rate': ['Unitary System Electricity Rate', 'Perimeter_ZN_1 ZN'],
    # 'z2_e_rate': ['Unitary System Electricity Rate', 'Perimeter_ZN_2 ZN'],
    # 'z3_e_rate': ['Unitary System Electricity Rate', 'Perimeter_ZN_3 ZN'],
    # 'z4_e_rate': ['Unitary System Electricity Rate', 'Perimeter_ZN_4 ZN']
}
actuators_tc = {
    'z0_cool_sp': ['Zone Temperature Control', 'Cooling Setpoint', 'Core_ZN ZN'],
    'z1_cool_sp': ['Zone Temperature Control', 'Cooling Setpoint', 'Perimeter_ZN_1 ZN'],
    'z2_cool_sp': ['Zone Temperature Control', 'Cooling Setpoint', 'Perimeter_ZN_2 ZN'],
    'z3_cool_sp': ['Zone Temperature Control', 'Cooling Setpoint', 'Perimeter_ZN_3 ZN'],
    'z4_cool_sp': ['Zone Temperature Control', 'Cooling Setpoint', 'Perimeter_ZN_4 ZN'],
    'z0_heat_sp': ['Zone Temperature Control', 'Heating Setpoint', 'Core_ZN ZN'],
    'z1_heat_sp': ['Zone Temperature Control', 'Heating Setpoint', 'Perimeter_ZN_1 ZN'],
    'z2_heat_sp': ['Zone Temperature Control', 'Heating Setpoint', 'Perimeter_ZN_2 ZN'],
    'z3_heat_sp': ['Zone Temperature Control', 'Heating Setpoint', 'Perimeter_ZN_3 ZN'],
    'z4_heat_sp': ['Zone Temperature Control', 'Heating Setpoint', 'Perimeter_ZN_4 ZN'],
}
weather_tc = {
    'oa_db_temp': 'outdoor_dry_bulb',
    'oa_rh': 'outdoor_relative_humidity'
}

timesteps = 20
# create calling point with actuation function
calling_point = 'callback_after_predictor_after_hvac_managers'

class Agent:
    def __init__(self):
        pass

    def observe(self):
        pass

    def act(self):

        # dbt, dbt_actuator, timestep = sim.get_ems_data(['oa_temp', 'act_odb_temp', 'timesteps'])

        # print(f'Action:  Timestep:{timestep}, DBT Act: {update_dbt}, DBT Current: {dbt}\n')

        return {
            'z0_heat_sp': 23, 'z0_cool_sp': 29,
            'z1_heat_sp': 23, 'z1_cool_sp': 29,
            'z2_heat_sp': 23, 'z2_cool_sp': 29,
            'z3_heat_sp': 23, 'z3_cool_sp': 29,
            'z4_heat_sp': 23, 'z4_cool_sp': 29
            }

    def c_to_f(self, temp_c: float):
        return 1.8 * temp_c + 32


# create building energy simulation obj
sim = emspy.BcaEnv(ep_path, ep_idf_to_run, timesteps, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc)
# create RL agent obj
agent = Agent()

sim.set_calling_point_and_callback_function(calling_point, None, None, True, 1, 1)
# sim.init_custom_dataframe_dict('custom_df', calling_point, 1, ['z0_cool_sp', 'setpoint_z0_cool_sp'])  # actuator lag
sim.init_custom_dataframe_dict('meters_hourly_df', calling_point, timesteps, meters_tc.keys())  # hourly meter

# RUN
sim.run_env(ep_weather_path)
sim.reset_state()

dfs = sim.get_df()
# dfs = sim.get_df(to_csv_file=cvs_output_path)

# move out folder to openstudio folder
# shutil.move('out', os_folder + '5office_small_ems' + '/out')





