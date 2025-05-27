import random
# import matplotlib as mat
from tkinter import *

# 2h2o -> 2h2 + o2
# 4h2 + co2 -> ch4 + 2h2o

#region important chemistry values for the simulation
molar_mass_hydrogen = 2.016  # g/mol
molar_mass_carbon_dioxide = 44.01 #g/mol
molar_mass_methane = 16.04  # g/mol
molar_mass_water = 18.01528 #g/mol
enthalpy_hydrogren = 0
enthalpy_oxygen = 0
enthalpy_carbon_dioxide = -393.5 #kJ/mol
enthalpy_methane = -74.8 #kJ/mol
enthalpy_water = -285.83 #kJ/mol

user_input_water = input("Enter the amount of water needed in kg: ")
user_input_float = float(user_input_water)

hydrolysis_kWh = random.randint(50, 56) ### in kWh/kg (per kg. of liquid water)
carbon_dioxide_gatherer = random.uniform(10.7, 106.4) ### in kg/per hour how much carbon can be gathered in an hour
total_moles_carbon_dioxide = (carbon_dioxide_gatherer*1000)/molar_mass_carbon_dioxide # in g/mol

total_moles_water = (user_input_float*1000)/molar_mass_water

total_energy_hydrolysis = abs((user_input_float*3600*hydrolysis_kWh)) #Kj/kg the kg was given in the user input
print("Energy needed to enact hydrolysis on " + str(user_input_float) + "Kg  of water = " + str(round(total_energy_hydrolysis, 3)) + " KJ")

#energy that is needed to turn carbon dioxide and dihydrogen into methane
total_moles_dihydrogen = total_moles_water
total_moles_methane = (total_moles_dihydrogen/4) 
mass_H2_needed_kg = (4 * molar_mass_hydrogen)/1000
needed_enthalpy_value = 250 #kJ/mol
#sabatier_energy_kWh = random.uniform(1.0, 2.0)

if (total_moles_carbon_dioxide <= total_moles_dihydrogen/4):
    total_moles_methane = total_moles_carbon_dioxide
elif (total_moles_carbon_dioxide > total_moles_dihydrogen/4):
    total_moles_methane = total_moles_dihydrogen/4
elif (total_moles_dihydrogen < (4*total_moles_carbon_dioxide)):
    print("You ain't got enough dihydrogen foo 🐱‍👤")
total_kg_methane = (total_moles_methane * molar_mass_methane)/1000

sabatier_energy_needed = abs(total_moles_methane*((enthalpy_methane+(2*enthalpy_water)))-((4*enthalpy_hydrogren) + enthalpy_carbon_dioxide)) # kJ

print("sabatier energy: "  + str(round(sabatier_energy_needed, 3)) + " KJ")

total_energy_needed = sabatier_energy_needed + total_energy_hydrolysis
print("Total Energy to produce methane from " + str(user_input_water) + "Kg of water = " + str(round(total_energy_needed, 2)), " kJ")
print("You will produce " + str(round(total_kg_methane, 4)) + " Kg of methane") 

'''
natural gas = 70-90% methane
so from what ive read
we have to account for the fact that the machine that we use doesn't have 100% efficiency.
and also there isnt any exact measurements of how much energy is produced from pure methane and only in natural gas.
this means more varied results and random.randint
'''

efficiency = round(random.uniform(0.33, 0.75), 2) #percentage of efficiency of the machine
percentage_of_methane_in_natural_gas = round(random.uniform(0.70,0.90), 2) # 70% to 90% of the natural gas is methane
max_power_released_methane = 15.4 # KWH/kg
max_power_released_methane_KJ = max_power_released_methane * 3600 #kJ/kg
energy_from_methane= (total_kg_methane * max_power_released_methane_KJ * efficiency) # KJ/kg
print ("Energy from methane: " + str(round(energy_from_methane, 3)) + " KJ")