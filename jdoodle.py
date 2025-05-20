import numpy as np

# Constants
colony = 50
starting_age = 22
start_size = 59  # in kg
avg_activity = 1.5  # in hours
avg_oxygen = np.random.normal(0.84, 0.02)  # kg per day
colony_number = colony


age_increase = 0.011      # 1.1% increase per year
body_size_increase = 0.01  # 1% per 3 kg
activity_increase = 0.305 # 30.5% per hour

class Person:
    def __init__(self):
        self.age = np.random.randint(22, 71)
        self.body_size = np.random.normal(59, 5)
        self.activity = np.random.normal(1.5, 1/6)

    def oxygen_consumption(self):
        # Percentage changes
        age_factor = (self.age - starting_age) * age_increase
        body_size_factor = ((self.body_size - start_size) / 3) * body_size_increase
        activity_factor = self.activity * activity_increase
        
        # Total percent change from baseline
        total_percent_change = age_factor + body_size_factor + activity_factor
        oxygen_needed = avg_oxygen * (1 + total_percent_change)
        return oxygen_needed

def simulate_colony(size=colony):
    people = [Person() for _ in range(size)]
    total_oxygen = sum(p.oxygen_consumption() for p in people)
    return total_oxygen, people


sizes_to_simulate = [25, 50, 75, 100, 125, 150]
repetitions = 10

with open(f"simulation_data.csv", "w") as f:
    f.write("Colony Size,Total Oxygen Consumption\n")
    print("Colony Size,Total Oxygen Consumption")

# Repeat 5 times for each colony size
for i in range(0, 5):
    for size in sizes_to_simulate:
        total_oxygen, colony = simulate_colony(size = size)
        
        # Save to CSV
        with open(f"simulation_data.csv", "a") as f:
            f.write(f"{size},{total_oxygen}\n")
            print(f"{size},{total_oxygen}")
print("Simulation complete.")