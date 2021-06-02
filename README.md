# RL-BCA (Work In Progress...)
### This repo is for reinforcement learning (RL) algorithm development and testing of BCA (Building Control Agent) on EnergyPlus (E+) 9.5 building energy simulator using Python Energy Management System (EMS) API using a meta-class wrapper.

*This repo was constructed by someone with little experience with EnergyPlus and software/programming, but wanted to assist in creating an easily interfacable RL 'environment' for intelligent HVAC control research.* 

The meta-class wrapper, EmsPy, is meant to simplify and somewhat constrain the E+ EMS API. The popular/intended use of EMS is to interface with a running E+ building simulation. Recently, an Python API was created for EMS so users aren't constrained to utilizing the E+ Runtime Language (ERL) and can more easily interact with a running simulation to gather state information and implement custom control at each simulation timestep (subhourly).
EMS exposes E+ data such as variables, internal variables, meters, actuators, and weather. Please see the documentation hyperlinks below to learn more. 

Although this repo is meant to facilitate in interfacing with E+ and open up this environment to more AI and controls people, a good understanding of E+ and building modeling may still be necessary, ecspecially if you intend to create and control your own building models. Eventually, some standard building testbed environments will be created and implemented so that user's can just interface with them through Python purely for control purposes. However, you will still need to have the E+ simulation engine downloaded. 

Further documentation:
- [EnergyPlus](https://energyplus.net/)
- [EnergyPlus Documentation](https://energyplus.net/documentation) *(including EMS Application Guide)*
- [EnergyPlus EMS Python API 0.2 Documentation](https://energyplus.readthedocs.io/en/stable/api.html)
- [OpenStudio SDK Documentation](http://nrel.github.io/OpenStudio-user-documentation/)
- [OpenStudio Coalition](https://openstudiocoalition.org/)
- [Unmet Hours Help Forum](https://unmethours.com/questions/)

![image](https://user-images.githubusercontent.com/65429130/119517258-764bbc00-bd45-11eb-97bf-1af9ab0444cb.png)



 
