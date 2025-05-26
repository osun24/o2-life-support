import random

sols_in_mars_years = 668

Pu_fission_rate = 10.0 #fission/s/kg
energy_per_fission = 3.318*(10^-11) # J/fission
energy_per_second = 3.318*(10^-10) #J/s/kg
efficiency = round(random.uniform(0.20, 0.25), 2) # based on dust and atmospheric pressure

user_input_mass = int(input("How many kg of Pu-239: ")) #kg

energy_from_nuclear = abs(energy_per_second*user_input_mass*efficiency)
print("Energy from nuclear: " + str(round(energy_from_nuclear, 2)) + " kJ/d")