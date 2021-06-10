 # RL-BCA (Work In Progress...)
### This repo is for reinforcement learning (RL) algorithm development and testing of BCAs (Building Control Agent) in EnergyPlus (E+) building energy simulator using Python Energy Management System (EMS) API with a <ins>meta-class wrapper, EmsPy</ins>.

*This repo was constructed by someone with little experience with EnergyPlus and software/programming, but wanted to 
assist in creating an easily interfacable RL 'environment' for intelligent HVAC control research. Any feedback/criticism is appreciated.* 

The meta-class wrapper, **EmsPy**, is meant to simplify and somewhat constrain the E+ EMS API. The popular/intended use of 
EMS is to interface with a running E+ building simulation, not so easily done otherwise. Recently, an Python API was 
created for EMS so users aren't constrained to using the E+ Runtime Language (ERL) and can more readily interact with 
a running building simulation to gather state information and implement custom control at each simulation timestep 
(subhourly). This API can be used to create Python plugins or use E+ as a library and run simulations from Python - EmsPy utilizies the latter method.  
EMS exposes E+ data such as variables, internal variables, meters, actuators, and weather. Please see the documentation 
hyperlinks below to learn more. 

Although this repo is meant to facilitate in interfacing with E+, making this environment more accessible to AI and controls 
people, a good understanding of E+ and building modeling may still be necessary, especially if you intend to create, link, and
 control your own building models. Eventually, some standard building models and template scripts will be created so that 
 user's can simply experiment with them through Python for control purposes with no E+ experience needed. This may help standardize benchmark performance. 
 
 Regardless of your use case, you will 
 need to have the proper versioned E+ simulation engine downloaded onto your system https://energyplus.net/downloads. 

### Further Documentation:
- [EnergyPlus](https://energyplus.net/)
- [EnergyPlus Documentation](https://energyplus.net/documentation) *(including EMS Application Guide!)*
- [EnergyPlus EMS Python API 0.2 Documentation](https://energyplus.readthedocs.io/en/stable/api.html)
- [EnerrgyPlus EMS API Homepage](https://nrel.github.io/EnergyPlus/api/)
- [OpenStudio SDK Documentation](http://nrel.github.io/OpenStudio-user-documentation/) (for building model creation and simulation GUI)
- [OpenStudio Coalition](https://openstudiocoalition.org/)
- [Unmet Hours Help Forum](https://unmethours.com/questions/) (community forum for EnergyPlus related help)

### Dependencies:
- EnergyPlus 9.5 (building energy simulation engine)
- EnergyPlus EMS Python API 0.2 (included in E+ 9.5 download)
- Python 3
- pyenergyplus Python package (included in E+ download)
- openstudio Python package

### Usage Explanation:

The diagram below depicts the RL-interaction-loop within a simulation timestep at runtime. Because of the technicalities of the 
interaction between EMS and the simulator - mainly the use of callback function(s) and multiple calling points available
 per timestep - the RL algorithm must be implemented in a very specific manner, which will be explained in 
detail below. 

<img src="https://user-images.githubusercontent.com/65429130/119517258-764bbc00-bd45-11eb-97bf-1af9ab0444cb.png" width = "750"> 

<br/>There are likely 4 main use-cases for this repo, if you are hoping to implement RL algorithms at runtime. In order of increasing complexity:

- You want to use an existing template and linked building model to purely implement RL control
- You have an existing E+ building model (with *no* model or .idf modification needed) that you want to link and 
implement RL control on
- You have an existing E+ building model (with *some amount* of model or .idf modification needed) that you want to 
link and implement RL control on
- You want to create a new E+ building model to integrate and implement RL control on

EmsPy usage for these use-cases is all the same, the difference is what must be done beforehand. Creating building models, 
understanding their file makeup, modifying .idf files, and adding/linking EMS variables and actuators brings extra challenges.
This guide will focus on utilizing EmsPy (EMS API meta-class wrapper), and the latter components needed before EmsPy will
be discussed briefly at the end, with basic guidance to get you started in the right direction. 

At the least, even if solely using EmsPy for a given model, it is important to understand the EMS Metrics of a given
model: variables, internal variables, meters, actuators, and weather. These are used to build the state and
action space of your control framework. See the EMS Application Guide and Input Output Reference documents for detailed
information on these elements https://energyplus.net/documentation.
  
### How to use EmsPy with an E+ Model:
 
This guide follows the design of the template Python scripts provided.

**1.** First, you will create an **EmsPy object** from proper inputs (this acts as your simulation/environment and agent). The inputs include paths to the E+ directory and the
building model file to be simulated, information about desired EMS metrics, simulation timestep, and actuation functions with 
calling points:   

```python
agent = emspy.BcaEnv(ep_path: str, ep_idf_to_run: str, timesteps: int, vars_tc: list, intvars_tc: list, meters_tc: list, actuators_tc: list, weather_tc: list)
```
- `ep_path` set the path to your EnergyPlus 9.5 installation directory
- `ep_idf_to_run` set the path to your EnergyPlus building model, likely .idf file
- `timesteps` set the number of timesteps per hour of the simulation
- define all EMS metrics you want to call or interact with in your model:
  - Build the Table of Contents (ToC) for EMS variables, internal variables, meters, actuators, and weather 
  - ***Note:*** *this requires an understanding of EnergyPlus model input and output files, especially for actuators*
  - Each EMS category ToC should be a nested list of each EMS metric and (besides meters and weather) its required arguments for
    fetching the 'handle' from the model. See Data Transfer API documentation for more info https://energyplus.readthedocs.io/en/stable/datatransfer.html      
    - Variable: [variable_name, variable_key] elements of `vars_tc` list
    - Internal [variable_type, variable_key] elements of `intvars_tc` list
    - Meter: [meter_name] element of `meter_tc` list
    - Actuator: [component_type, control_type, actuator_key] elements of `actuators_tc` list
    - Weather: [weather_name] elements of `weather_tc` list
 
Once this has been completed the meta-class, ***EmsPy***, has all it needs to build out your class, implementing various data collection/organization and dataframes attributes, as well as finding the EMS handles from the ToCs, etc. It may be helpful to run this 'agent/environment' object initialization and then review its contents to see all that the meta-class has created. 

***Note:*** *At this point, the <ins>simulation can be ran</ins> but nothing useful will happen (in terms of control or data collection) as no calling points, callback functions, or actuation functions have been defined and linked.* 
 
**2.** Next, you must define the Calling Point & Actuation Function dictionary to define and enable callback functionality at runtime. This dictionary links a calling point(s) to a callback function(s) and arguments related to data/actuation update frequencies.
 A given <ins>calling point</ins> defines when a *linked* <ins>callback function</ins> (and optionally an <ins>actuation function </ins>) will be ran during the simulation timestep calculations.
 The diagram above represents the simulation flow and RL integration with calling points and callback functions. The Calling Point & Actuation Function dictionary should be built one key-value at a time using the method: 

 ```python
 BcaEnv.set_calling_point_and_actuation_function(calling_point: str, actuation_fxn, update_state: bool, update_state_freq: int = 1, update_act_freq: int = 1)
 ```
- `calling_point` set a single calling point from the available list `EmsPy.available_calling_points`
- `actuation_fxn` set as the control algorithm function (one of potentially many throughout a timestep), which must take no agruments and returns a dictionary (or `None`) of actuator name(s) (key) and setpoint value(s) (value) to be implemented at the linked calling point
- `update_state` set to T/F to whether or not the entire EMS ToCs should be updated for that calling point
- `update_state_freq` set to the number of simulation timesteps in between each state update, default is every timestep
- `update_act_freq` set to the number of simulation timesteps in between each actuation function call and actuation, default is every timestep
   
***Note:*** *that there are multiple calling points per timestep, each signifying the start/end of an event in the process. The majority of calling points occur consistently throughout the simulation, but several occur *once* before during simulation setup.* 

The user-defined <ins>actuation function</ins> should encapsulate any sort of control algorithm (more than one can be created and linked to unique calling points, but it's likely that only one will be used as the entire RL algorithm). Using the 'agent/environment' object attributes, or methods `BcaEnv.get_ems_data` and `BcaEnv.get_weather_forecast`, to collect state information, a control algorithm/function can be created and passed to this method. Using a decorator function, this actuation function will automatically be attached to a base callback function and linked to the defined calling point.
The rest of the arguments are also automatically passed to the base-callback function to dictate the update frequency of state data and actuation. This means that data collection or actuation updates do not need to happen every timestep. 

```python
BcaEnv.get_ems_data(ems_metric_list: list, time_rev_index: list) -> list
```

```python
BcaEnv.get_weather_forecast(when: str, weather_metrics: list, hour: int, zone_ts: int) -> list
```

 ***Note*** *: If you wish to use callback functions just for data collection and no actuation/control at a specific calling point, pass `None` as the actuation function.*
 
 ***Warning*** *: EMS data (and actuation) can be updated <ins>for each calling point</ins> (and actuation function) assigned within a single timestep. You likely want to avoid this and manually only implement one state update `state_update=True` per timestep. Otherwise, you will screw up zone timestep increments (with current software design) and may accidentally be collecting data and actuating multiple times per timestep.
 An understanding of calling points and when to collect data or actuate is ***crucial*** - Please see the [EMS Application Guide](https://energyplus.net/documentation) for more information on calling points.*
  
           
**TIPS**:

**CAUTION**:
- EMS data (and actuation) can be updated for each calling point (and actuation function) assigned for a single timestep, you may want to avoid this and manually only implement one state update per timestep. Otherwise, you will screw up zone timestep incremts (???) and may accidently be collecting data and actuating multiple times per timestep. 
- Make sure your hourly timestep matches that of your EnergyPlus .idf model

### References:

### TODO:
what if users only want to collect certain EMS data at a calling point, as opposed to updating ALL data, need to create functionality for this (???????????????????????????)
