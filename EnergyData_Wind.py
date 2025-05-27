import random
import numpy as np

airDensity = 0.02 # kg/m^3
windSpeed = round(np.uniform(0.0, 7.0), 2)
efficiency = round(np.uniform(0.30, 0.5), 2)

user_input = input("How long are the turbine blades : ")

sweptArea = 3.1 * (user_input^2) # m^2
powerGenerated = 0.5 * airDensity * sweptArea * windSpeed # Wh
energyGenerated = ((powerGenerated * 3600)/1000) * efficiency # kJ/hour

print(energyGenerated)