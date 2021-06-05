 # RL-BCA (Work In Progress...)
### This repo is for reinforcement learning (RL) algorithm development and testing of BCA (Building Control Agent) on EnergyPlus (E+) 9.5 building energy simulator using Python Energy Management System (EMS) API with a meta-class wrapper.

*This repo was constructed by someone with little experience with EnergyPlus and software/programming, but wanted to assist in creating an easily interfacable RL 'environment' for intelligent HVAC control research.* 

The meta-class wrapper, EmsPy, is meant to simplify and somewhat constrain the E+ EMS API. The popular/intended use of EMS is to interface with a running E+ building simulation. Recently, an Python API was created for EMS so users aren't constrained to utilizing the E+ Runtime Language (ERL) and can more easily interact with a running simulation to gather state information and implement custom control at each simulation timestep (subhourly).
EMS exposes E+ data such as variables, internal variables, meters, actuators, and weather. Please see the documentation hyperlinks below to learn more. 

Although this repo is meant to facilitate in interfacing with E+ and open up this environment to more AI and controls people, a good understanding of E+ and building modeling may still be necessary, ecspecially if you intend to create and control your own building models. Eventually, some standard building testbed environments will be created and implemented so that user's can just interface with them through Python purely for control purposes. However, you will still need to have the E+ simulation engine downloaded. 

### Further documentation:
- [EnergyPlus](https://energyplus.net/)
- [EnergyPlus Documentation](https://energyplus.net/documentation) *(including EMS Application Guide!)*
- [EnergyPlus EMS Python API 0.2 Documentation](https://energyplus.readthedocs.io/en/stable/api.html)
- [OpenStudio SDK Documentation](http://nrel.github.io/OpenStudio-user-documentation/)
- [OpenStudio Coalition](https://openstudiocoalition.org/)
- [Unmet Hours Help Forum](https://unmethours.com/questions/)

### Dependencies
- E+ (building energy simulation engine)
- pyenergyplus Python package (included in E+ download)
- openstudio Python package

### Usage Explanation

The image below depicts the RL-loop within a simulation timestep at runtime. Because of the technicalities of the interaction between EMS and the simulator - mainly the use of callback function(s) and multiple calling point opportunties per timestep - the RL algorithm must be implemented in a very specific manner, which will be explained in detail below. 

<img src="https://user-images.githubusercontent.com/65429130/119517258-764bbc00-bd45-11eb-97bf-1af9ab0444cb.png" width = "750"> 

There are likely 4 main use-cases for this repo, if you are hoping to implement RL algorithms at runtime.

They are, in order of increasing complexity:
1. You want to use an existing pre-integrated template to purely implement RL control
2. You have an existing E+ building model (with no model or .idf modification needed) that you want to integrate and implement RL control
3. You have an existing E+ building model (with some amount of model or .idf modification needed) that you want to integrate and implement RL control
4. You want to create a new E+ building model to integrate and implement RL control

How to use EmsPy with your E+ model (this guide follows along with the template scripts provided):

1. First you will create an EmsPy object (agent) given proper inputs. The inputs include paths to the E+ directory and
building model to be simulated, information about desired EMS metrics, simulation timestep, and actuation functions with 
calling points.  
    - define the path to your EnergyPlus 9.5 directory
    - define the path to your EnergyPlus building model (likely .idf file)
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
    - define the Calling Point and Actuation Function dictionary. This sets when a callback function(s), possibly assigned with
    a user-defined actuation function(s) (RL algorithm), will be called at each timestep. There are multiple calling points per
    timestep. The diagram above represents the simulation flow. An understanding of calling points and when to collect data
    actuate is crucial - Please the EMS Application Guide for more information on calling points.
        - for each element in this dictionary. This key is the calling point at which the value tuple will be implemented
        - the dictionary value must contain:
            - an actuation function (or None) which returns a nested list of actuator variables and their desired value to be set
            - True/False of whether or not the state should be updated at this calling point for a given timestep (it is
            recommended that this only be done once per timestep, so be carefull if implmenting multiple callbacks per timestep)
            - frequency of timesteps when the state space should be updated.................
    