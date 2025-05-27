import random
from tkinter import *
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# https://madeblue.org/en/how-much-water-do-you-use-per-day/ 
# https://www.mayoclinic.org/healthy-lifestyle/nutrition-and-healthy-eating/in-depth/water/art-20044256

# Constants
colony = 50
starting_age = 25
start_size = 59  # in kg
avg_activity = 1.5  # in hours
# avg_oxygen = np.random.normal(0.84, 0.02)  # kg per day
colony_float = float(colony)
total_hours = 1.02749125 * 24
water_intake = 0

# for i in range(colony/2):
#     water_intake_female = random.uniform(1.5, 22.5)
#     total_intake_female += (water_intake_female)
# for i in range(colony/2):
#     water_intake_male = random.uniform(2.5, 3.5)
#     total_intake_male += (water_intake_male)
# total_intake = (total_intake_female+total_intake_male)

# age_increase = 0.01        # 1% per year
# body_size_exponent = 0.67  # VO₂ proportional to mass^0.67 (VO2 max corresponds with oxygen consumption)
# activity_increase = 0.32   # 32% per hour

"""Males: VO2max/kg = - 0.0049 × age2 + 0.0884 × age + 48.263 (R2 = 0.9859; SEE = 1.4364) Females: VO2max/kg = - 0.0021 × age2 - 0.1407 × age + 43.066 (R2 = 0.9989; SEE = 0.5775)."""

class Water_Person:
    def __init__(self):
        self.age = np.random.beta(2, 8) * (70 - starting_age) + starting_age # skewed towards younger ages
        self.activity = np.random.normal(1.5, 0.25)
        self.is_male = np.random.choice([True, False])
        
        if self.is_male:
            self.body_size = np.random.normal(80.3, 9.5) # mass (kg)
        else:
            self.body_size = np.random.normal(67.5, 9.4) # mass (kg)

    def water_consumption(self):
        global water_intake
        water_intake = (self.body_size * 0.035)
        
        actual_age = ((self.age) - starting_age)
        age_factor = 1/(1+((self.age) - starting_age) * 0.001) # made to 
        water_for_activity = self.activity # hours of overall activity per day

        # print("Is male : " + str(self.is_male))
        # print("age is : " + str(self.age) + "/" + str(age_factor)) #years   
        # print("size is : " + str(self.body_size) + "/" + str(water_intake)) #kg
        # print("Activity is : "  + str(self.activity) + "/" + str(water_for_activity)) #kg
        
        total_water = (water_intake * age_factor) + water_for_activity # L/day

        return total_water

    
    # exercise_oxygen = vo2max * 0.70 * self.body_size * self.activity * 60  # mL
    # resting_oxygen = 3.5 * self.body_size * (total_hours - self.activity) * 60  # mL

    # total_oxygen_ml = exercise_oxygen + resting_oxygen
    # oxygen_kg = total_oxygen_ml / 1000 * 1.429 / 1000 # Convert mL to kg (1.429 g/L at STP)
    # return oxygen_kg

# colony = np.random.randint(10, 125, size=100)  # Random colony sizes between 1 and 100

w = Water_Person()
# print(w.water_consumption())

# repeat 5 times 
def simulate_colony(size=colony): # This is for the separate simulation script
    people = [Water_Person() for _ in range(size)]
    total_water_consumed = sum(p.water_consumption() for p in people)
    return total_water_consumed, people
# print(water_consumption())
  # Random colony sizes between 1 and 100

# The following part is for generating simulation_data.csv and is not directly part of the vis tool
if __name__ == "__main__": # Protect this part from running on import
    with open(f"simulation_data.csv", "w") as f:
        f.write("Colony Size,Total Water Consumption\n")
        # Print header to console as well, mimicking original
        print("Colony Size,Total Water Consumption")

    for size in range(1, colony+1):
        # simulate_colony now returns consumption and people list
        total_water_consumption, _ = simulate_colony(size=size)
        
        print(f"Colony: {size}, Avg Consumption: {total_water_consumption/size:.2f} liters per person, Total Consumption: {total_water_consumption}")
    print("Simulation for CSV complete.")