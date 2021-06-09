 # RL-BCA (Work In Progress...)
### This repo is for reinforcement learning (RL) algorithm development and testing of BCAs (Building Control Agent) in EnergyPlus (E+) building energy simulator using Python Energy Management System (EMS) API with a <ins>meta-class wrapper, EmsPy</ins>.

*This repo was constructed by someone with little experience with EnergyPlus and software/programming, but wanted to 
assist in creating an easily interfacable RL 'environment' for intelligent HVAC control research.* 

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

<br/>There are likely 4 main use-cases for this repo, if you are hoping to implement RL algorithms at runtime.

They are, in order of increasing complexity:
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

1. First, you will create an **EmsPy object** from proper inputs (this acts as your simulation/environment and agent). The inputs include paths to the E+ directory and the
building model file to be simulated, information about desired EMS metrics, simulation timestep, and actuation functions with 
calling points:   

```python
agent = emspy.BcaEnv(ep_path, ep_idf_to_run, timesteps, vars_tc, int_vars_tc, meters_tc, actuators_tc, weather_tc)
```
- set the path to your EnergyPlus 9.5 installation directory
- set the path to your EnergyPlus building model, likely .idf file
- set the number of timesteps per hour of the simulation
- define all EMS metrics you want to call or interact with in your model
        - Build the Table of Contents (TC) for EMS variables, internal variables, meters, actuators, and weather 
        (this requires an understanding of EnergyPlus model input and output files, especially for actuators)
        - Each EMS category TC should be a list with nested lists of each EMS metric and its required arguments for
        fetching the 'handle' from the model. See Data Transfer API documentation for more info https://eplus.readthedocs.io/en/stable/datatransfer.html
             - Variable: [variable_name, variable_key]
             - Internal [variable_type, variable_key]
             - Meter: [meter_name]
             - Actuator: [component_type, control_type, actuator_key]
             - Weather: [weather_name]
 
Once this has been completed the meta-class, ***EmsPy***, has all it needs to build out the class to create various data collection/organization and dataframes attributes, as well as find the EMS handles from the ToCs, etc. It may be helpful to run this 'agent' object initialization and then review its contents to see all that the meta-class has created. *At this point, the simulation can be ran but nothing useful will happen, in terms of control and data collection, as no calling points, callback functions, or actuation functions have been defined.* 
 
2. Next, you must define the Calling Point & Actuation Function dictionary to enable callback functionality at runtime. This dictionary links a calling point(s) to a callback function(s) and arguments related to data/actuation update frequencies. This dictionary should be built one key-value at a time using: 

 ```python
 BcaEnv.get_ems_data(calling_point: str, actuation_fxn, update_state: bool, update_state_freq: int = 1, update_act_freq: int = 1)
 ```
 
A given <ins>calling point</ins> defines when a linked callback function will be ran during the simulation timestep calculations. Note that there are multiple calling points per timestep, each signfying the start/end of an event in the process. The majority of calling points occur consistently throughout the simulation, but several occur *once* before during simulation setup. 
The <ins>actuation function</ins> should encapsulate any sort of control algorithm (more than one can be created and linked to unqiue calling points, but it's likely that only one will be used as the entire RL algorithm. Using the 'agent' object attributes to collect state information, a control algorithm/function can be created by the user and then passed to this method. This function should return a dictionary (???) of the actuator variables (key) and set values (value). Using a decorator function, this actuation function will automatically be attached to a base callback function and the defined calling point.
The rest of the arguments are also automatically passed to the base-callback function to dictate the update frequency of state data and actuation. This means that data collection or actuation updates do not need to have every timestep. 
 
 * ***Note***: if you wish to just use callback functions just for data collection, pass `None` (???) for the actuation function.*
 
 * ***Warning***: EMS data (and actuation) can be updated for each calling point (and actuation function) assigned for a single timestep, you may want to avoid this and manually only implement one state update per timestep. Otherwise, you will screw up zone timestep increments (???) and may accidently be collecting data and actuating multiple times per timestep.*

The diagram above represents the simulation flow. An understanding of calling points and when to collect data or actuate is crucial - Please see the EMS Application Guide for more information on calling points. The default callback function can include a user-defined actuation function(s) (RL algorithm) and several other parameters. This is to all be defined in the Calling Point & Actuation Function dictionary. 
    - for each element in this dictionary. This key is the calling point at which the value tuple will be 
      implemented
    - the dictionary value must contain:
    - an actuation function (or None) which returns a nested list of actuator variables and their desired value 
      to be set
    - True/False of whether or not the state should be updated at this calling point for a given timestep (it is
       recommended that this only be done once per timestep, so be carefull if implmenting multiple callbacks per 
       timestep)
    - frequency of timesteps when the state space should be updated.................
           
TIPS:

CAUTION:
- EMS data (and actuation) can be updated for each calling point (and actuation function) assigned for a single timestep, you may want to avoid this and manually only implement one state update per timestep. Otherwise, you will screw up zone timestep incremts (???) and may accidently be collecting data and actuating multiple times per timestep. 
- Make sure your hourly timestep matches that of your EnergyPlus .idf model

### References:
