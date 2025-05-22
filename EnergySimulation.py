import random
import matplotlib as mat
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

user_input2 = float(input("Enter the amount of water needed in kg: "))
hydrolysis_kWh = random.randint(50, 56) # in kWh/kg (per kg. of liquid water)
carbon_dioxide_gatherer = random.randint()

#this section is to figure out how much energy is needed to seperate water molecule into the oxygen and hydrogen atoms. 


total_moles_water = (user_input2*1000)/molar_mass_water

# for example the amount of moles of water in total_moles_water i is 50 moles of water, then that means you'd have to subtracct that by the amount of moles of O atomos there are. 

hydrolysis_kJ = total_moles_water*(hydrolysis_kWh*3600)/(molar_mass_water*1000)
print("hydrolysis in Kj: ", hydrolysis_kJ) # KJ/kg
total_energy_hydrolysis = (user_input2*3600*hydrolysis_kWh) #Kj/kg the kg was given in the user input


print("Energy needed to enact hydrolysis on " + str(user_input2) + "Kg  of water = " + str(total_energy_hydrolysis) + "KJ")


#endregion
 






#energy that is needed to turn carbon dioxide and dihydrogen into methane


total_moles_dihydrogen = total_moles_water #example 80moles of water 80h2 + 40o2
total_moles_methane = (total_moles_dihydrogen/4) 


#total_moles_dihydrogen = total_moles_water/
sabatier = 0.5 * (molar_mass_hydrogen + molar_mass_carbon_dioxide) / molar_mass_methane  # energy needed to produce methane
mass_H2_needed_kg = (4 * molar_mass_hydrogen)/1000

needed_enthalpy_value = 250 #kJ/mo
# energy NEEDED to split water
sabatier_energy_kWh = random.uniform(1.0, 2.0)



# CONSTANTS

energy_needed = total_moles_methane*((enthalpy_methane+(2*enthalpy_water)))-((4*enthalpy_hydrogren) + enthalpy_carbon_dioxide) # kJ


# energy_needed_deviation = np.random.normal(energy_needed, 30) # we are trying to get a devation of 30 kJ

# if energy_needed == 30+neededenthalpyvalue:
#     print("Energy needed to produce methane: ", energy_needed_deviation, "kJ")
# elif energy_needed == 30-neededenthalpyvalue:
#     print("Energy needed to produce methane: ", energy_needed, "kJ")

print("Energy needed to produce methane: ", energy_needed, "kJ")
# x= mass of methane y= energy needed.