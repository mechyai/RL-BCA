import os
import matplotlib.pyplot as plt
import pandas as pd

import openstudio  # ver 3.2.0 !pip list
from EmsPy import emspy

# work arouund # TODO find reference to error correction
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
# OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized.

ep_path = 'A:/Programs/EnergyPlusV9-5-0/'
ep_idf_to_run = ''
ep_weather_path = ''
# ep_os_to_run = ''

project_name = '5office_small_prototype_FL/'
project_path = 'A:/Files/PycharmProjects/RL-BCA/ModelRunTests/DemoControl/'

cvs_output_path = ''

# --- create EMS Table of Contents (TC) for sensors/actuators ---
# vars_tc = {"attr_handle_name": ["variable_type", "variable_key"],...}
# int_vars_tc = {"attr_handle_name": "variable_type", "variable_key"],...}
# meters_tc = {"attr_handle_name": "meter_name",...}
# actuators_tc = {"attr_handle_name": ["component_type", "control_type", "actuator_key"],...}
# weather_tc = {"attr_name": "weather_metric",...}
vars_tc = None
int_vars_tc = None
meters_tc = None
actuators_tc = None
weather_tc = None
timesteps = #
# create calling point with actuation function
calling_point = ''

# create building energy simulation obj
sim = emspy.BcaEnv(ep_path, ep_idf_to_run, timesteps, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc)

class Agent:
    def __init__(self):
        pass

    def observe(self):
        pass

    def act(self):
        pass

# create RL agent obj
agent = Agent()

sim.set_calling_point_and_callback_function(calling_point, agent.observe, agent.act, True, 1, 1)

sim.run_env(ep_weather_path)
sim.reset_state()




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

        return {'heating_sp': 20, 'cooling_sp': 22}

    def c_to_f(self, temp_c: float):
        return 1.8 * temp_c + 32



# agent2 = Agent()



