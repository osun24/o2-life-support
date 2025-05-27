import random
# import tkinter as tk
from tkinter import *
import matplotlib.pyplot as plt
import numpy as np

sols_in_mars_year = 668

solar_irradiance_earth = 1361.0 #W/m^2
solar_irradience_mars = 586.0 #W/m^2
solar_panel_efficiency = round(random.uniform(0.20, 0.27),2) #15-20% efficiency
dust_efficiency = round(random.uniform(0.5, 0.9),2) #10-50% inefficiency

user_input_area = float(input("How many m^2 of solar panels: "))

energy_from_solar = (solar_irradience_mars*user_input_area*0.001*44387*solar_panel_efficiency*dust_efficiency) #kJ/d
print("Energy from solar: " + str(energy_from_solar))