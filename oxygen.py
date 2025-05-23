import numpy as np

# Constants
colony = 50
starting_age = 22
start_size = 59  # in kg
avg_activity = 1.5  # in hours
avg_oxygen = np.random.normal(0.84, 0.02)  # kg per day
colony_number = colony
total_hours = 1.02749125 * 24
o2_per_m2_of_plant = 61 * colony * 1/100 # kg PER DAY
CROP_METERS_PER_PERSON = 61  # m² per person

age_increase = 0.01        # 1% per year
body_size_exponent = 0.67  # VO₂ proportional to mass^0.67 (VO2 max corresponds with oxygen consumption)
activity_increase = 0.32   # 32% per hour

"""Males: VO2max/kg = - 0.0049 × age2 + 0.0884 × age + 48.263 (R2 = 0.9859; SEE = 1.4364) Females: VO2max/kg = - 0.0021 × age2 - 0.1407 × age + 43.066 (R2 = 0.9989; SEE = 0.5775)."""

class Person:
    def __init__(self):
        self.age = np.random.beta(2, 8) * (70 - starting_age) + starting_age # skewed towards younger ages
        self.activity = np.random.normal(1.5, 1/6)
        self.is_male = np.random.choice([True, False])
        
        self.body_size = np.random.normal(67.5, 13.8) # mass (kg)
        if self.is_male:
            self.body_size = np.random.normal(80.3, 13.5)

    def oxygen_consumption(self):
        if self.is_male:
            vo2max = -0.0049 * self.age ** 2 + 0.0884 * self.age + 48.263  # mL/kg/min
        else:
            vo2max = -0.0021 * self.age ** 2 - 0.1407 * self.age + 43.066  # mL/kg/min
        exercise_oxygen = vo2max * 0.70 * self.body_size * self.activity * 60  # mL
        resting_oxygen = 3.5 * self.body_size * (total_hours - self.activity) * 60  # mL

        total_oxygen_ml = exercise_oxygen + resting_oxygen
        oxygen_kg = total_oxygen_ml / 1000 * 1.429 / 1000 # Convert mL to kg (1.429 g/L at STP)
        return oxygen_kg
    
def oxygen_consumption(size = colony):
    people = [Person() for _ in range(size)]
    total_oxygen = sum(p.oxygen_consumption() for p in people)
    return total_oxygen

def oxygen_production(meters):
    # Assuming each person contributes equally to the oxygen production
    # and that the plants are producing oxygen at a constant rate
    total_oxygen = o2_per_m2_of_plant * meters
    return total_oxygen

def simulate_colony(size=colony):
    people = [Person() for _ in range(size)]
    total_oxygen = sum(p.oxygen_consumption() for p in people)
    total_oxygen += oxygen_production(size * CROP_METERS_PER_PERSON)  # Add the oxygen produced by plants
    return total_oxygen, people

sizes_to_simulate = np.random.randint(10, 125, size=100)  # Random colony sizes between 1 and 100

with open(f"simulation_data.csv", "w") as f:
    f.write("Colony Size,Total Oxygen Consumption\n")
    print("Colony Size,Total Oxygen Consumption")

# Repeat 5 times for each colony size
for size in sizes_to_simulate:
    total_oxygen, colony = simulate_colony(size = size)
    
    # Save to CSV
    with open(f"simulation_data.csv", "a") as f:
        f.write(f"{size},{total_oxygen}\n")
        print(f"Average: {total_oxygen/size} kg per person")
print("Simulation complete.")