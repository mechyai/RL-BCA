import os
import matplotlib.pyplot as plt
import pandas as pd

import openstudio  # ver 3.2.0 !pip list
from EmsPy import emspy

# work arouund # TODO find reference to error correction
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
# OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized.

ep_path = 'A:/Programs/EnergyPlusV9-5-0/'
ep_idf_to_run = 'A:/Files/PycharmProjects/RL-BCA/OpenStudio_Models/idf_files/5office_small_ems.idf'
ep_weather_path = 'A:/Files/PycharmProjects/RL-BCA/OpenStudio_Models/5office_small_ems/files/USA_FL_Tampa-MacDill.AFB.747880_TMY3.epw'
cvs_output_path = 'default_dfs'

# --- create EMS Table of Contents (TC) for sensors/actuators ---
# vars_tc = {"attr_handle_name": ["variable_type", "variable_key"],...}
# int_vars_tc = {"attr_handle_name": "variable_type", "variable_key"],...}
# meters_tc = {"attr_handle_name": "meter_name",...}
# actuators_tc = {"attr_handle_name": ["component_type", "control_type", "actuator_key"],...}
# weather_tc = {"attr_name": "weather_metric",...}
vars_tc = {
    'oa_wb_temp': ['Zone Outdoor Air Wetbulb Temperature', 'Core_ZN ZN'],
    'zone0_temp': ['Zone Air Temperature', 'Core_ZN ZN'],
    'zone1_temp': ['Zone Air Temperature', 'Perimeter_ZN_1 ZN'],
    'zone2_temp': ['Zone Air Temperature', 'Perimeter_ZN_2 ZN'],
    'zone3_temp': ['Zone Air Temperature', 'Perimeter_ZN_3 ZN'],
    'zone4_temp': ['Zone Air Temperature', 'Perimeter_ZN_4 ZN'],
    'zone0_rh': ['Zone Air Relative Humidity', 'Core_ZN ZN'],
    'zone1_rh': ['Zone Air Relative Humidity', 'Perimeter_ZN_1 ZN'],
    'zone2_rh': ['Zone Air Relative Humidity', 'Perimeter_ZN_2 ZN'],
    'zone3_rh': ['Zone Air Relative Humidity', 'Perimeter_ZN_3 ZN'],
    'zone4_rh': ['Zone Air Relative Humidity', 'Perimeter_ZN_4 ZN'],
}
int_vars_tc = None
meters_tc = None
actuators_tc = {
    'zone0_cool_sp': ['Zone Temperature Control', 'Cooling Setpoint', 'Core_ZN ZN'],
    'zone1_cool_sp': ['Zone Temperature Control', 'Cooling Setpoint', 'Perimeter_ZN_1 ZN'],
    'zone2_cool_sp': ['Zone Temperature Control', 'Cooling Setpoint', 'Perimeter_ZN_2 ZN'],
    'zone3_cool_sp': ['Zone Temperature Control', 'Cooling Setpoint', 'Perimeter_ZN_3 ZN'],
    'zone4_cool_sp': ['Zone Temperature Control', 'Cooling Setpoint', 'Perimeter_ZN_4 ZN'],
    'zone0_heat_sp': ['Zone Temperature Control', 'Heating Setpoint', 'Core_ZN ZN'],
    'zone1_heat_sp': ['Zone Temperature Control', 'Heating Setpoint', 'Perimeter_ZN_1 ZN'],
    'zone2_heat_sp': ['Zone Temperature Control', 'Heating Setpoint', 'Perimeter_ZN_2 ZN'],
    'zone3_heat_sp': ['Zone Temperature Control', 'Heating Setpoint', 'Perimeter_ZN_3 ZN'],
    'zone4_heat_sp': ['Zone Temperature Control', 'Heating Setpoint', 'Perimeter_ZN_4 ZN'],
}
weather_tc = {
    'oa_db_temp': 'outdoor_dry_bulb',
    'oa_rh': 'outdoor_relative_humidity'
}

timesteps = 30
# create calling point with actuation function
calling_point = 'callback_after_predictor_after_hvac_managers'

class Agent:
    def __init__(self):
        self.day = ''
        pass

    def observe(self):
        oa_temp, z_temp, heat_sp, cool_sp, timestep, datetime = sim.get_ems_data(['oa_temp', 'zone_temp', 'heating_sp', 'cooling_sp', 'timesteps', 'time_x'])

        current_day = datetime.strftime('%d')
        if current_day != self.day:
            print('--- New Day ---')

        print(f'Time: {datetime.strftime("%m/%d, %I:%M %p")}, TS:{round(timestep,2)}, '
              f'Act: {[round(self.c_to_f(heat_sp),2), round(self.c_to_f(cool_sp),2)]}, Zone T: {round(self.c_to_f(z_temp),2)} f, Outdoor T: {round(self.c_to_f(oa_temp),2)} f')
        self.day = datetime.strftime('%d')

        pass

    def act(self):

        # dbt, dbt_actuator, timestep = sim.get_ems_data(['oa_temp', 'act_odb_temp', 'timesteps'])

        # print(f'Action:  Timestep:{timestep}, DBT Act: {update_dbt}, DBT Current: {dbt}\n')

        return {'zone0_heat_sp': 23, 'zone0_cool_sp': 29,
                'zone1_heat_sp': 23, 'zone1_cool_sp': 29,
                'zone2_heat_sp': 23, 'zone2_cool_sp': 29,
                'zone3_heat_sp': 23, 'zone3_cool_sp': 29,
                'zone4_heat_sp': 23, 'zone4_cool_sp': 29}

    def c_to_f(self, temp_c: float):
        return 1.8 * temp_c + 32


# create building energy simulation obj
sim = emspy.BcaEnv(ep_path, ep_idf_to_run, timesteps, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc)
# create RL agent obj
agent = Agent()

sim.set_calling_point_and_callback_function(calling_point, None, agent.act, True, 1, 1)
sim.run_env(ep_weather_path)
sim.reset_state()

dfs = sim.get_df(to_csv_file=cvs_output_path)





