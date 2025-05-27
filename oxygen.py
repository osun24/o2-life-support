import numpy as np

# Constants
colony = 50
starting_age = 25
start_size = 59  # in kg
avg_activity = 1.5  # in hours
avg_oxygen = np.random.normal(0.84, 0.02)  # kg per day
colony_number = colony
total_hours = 1.02749125 * 24

# --- MODIFIED/NEW OXYGEN PRODUCTION RATES ---
o2_per_m2_of_algae = .4/1000  # kg PER DAY per m^2 (This was o2_per_m2_of_plant)
o2_per_m2_of_potatoes = 13.5/1000          # kg PER DAY per m^2 for potatoes (NEW)
# --- END MODIFIED/NEW ---

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
        # BMR roughly 3.5 mL/kg/min. Assume active work is 70% of VO2max.
        exercise_oxygen = vo2max * 0.70 * self.body_size * self.activity * 60  # mL for active period
        resting_oxygen = 3.5 * self.body_size * (total_hours - self.activity) * 60  # mL for resting period

        total_oxygen_ml = exercise_oxygen + resting_oxygen
        # Convert mL O2 to kg O2. Density of O2 is approx 1.429 g/L at STP.
        # 1 mL = 0.001 L. So, mass_g = (total_oxygen_ml / 1000) * 1.429
        # mass_kg = mass_g / 1000
        oxygen_kg = total_oxygen_ml / 1000000 * 1.429
        return oxygen_kg
    
def oxygen_consumption(size = colony): # This function seems to be for the separate simulation script, not directly used by vis.py's Person instances.
    people = [Person() for _ in range(size)]
    total_oxygen = sum(p.oxygen_consumption() for p in people)
    return total_oxygen

# --- MODIFIED OXYGEN PRODUCTION FUNCTION ---
def oxygen_production(algae_meters, potato_meters):
    # Calculate oxygen from algae
    oxygen_from_algae = o2_per_m2_of_algae * algae_meters
    # Calculate oxygen from potatoes
    oxygen_from_potatoes = o2_per_m2_of_potatoes * potato_meters
    # Total oxygen production
    total_oxygen = oxygen_from_algae + oxygen_from_potatoes
    return total_oxygen
# --- END MODIFIED ---

def simulate_colony(size=colony): # This is for the separate simulation script
    people = [Person() for _ in range(size)]
    # This function's oxygen calculation is different, assuming it's for a different purpose.
    # For the vis script, production is handled separately.
    total_oxygen_consumed = sum(p.oxygen_consumption() for p in people)
    
    # The original simulate_colony added production based on CROP_METERS_PER_PERSON
    # This might need updating if it's meant to reflect the new dual-source production
    # For now, assuming this function is not directly used by the visualization in the same way.
    # If it were, it would need algae_meters and potato_meters.
    # total_oxygen_produced_sim_colony = oxygen_production(algae_m, potato_m) 
    # net_oxygen_sim_colony = total_oxygen_produced_sim_colony - total_oxygen_consumed
    
    # The return value was net oxygen. Let's keep it focused on consumption for now
    # or clarify how production should be integrated here.
    # For the CSV generation part, it seems it was writing total_oxygen (which was net).
    # I will adjust simulate_colony to reflect consumption here, as the vis handles net.
    return total_oxygen_consumed, people


# The following part is for generating simulation_data.csv and is not directly part of the vis tool
if __name__ == "__main__": # Protect this part from running on import
    sizes_to_simulate = np.random.randint(10, 125, size=100)

    with open(f"simulation_data.csv", "w") as f:
        f.write("Colony Size,Total Oxygen Consumption\n")
        # Print header to console as well, mimicking original
        print("Colony Size,Total Oxygen Consumption")

    for size in sizes_to_simulate:
        # simulate_colony now returns consumption and people list
        total_o2_consumption, _ = simulate_colony(size=size)
        
        with open(f"simulation_data.csv", "a") as f:
            # The CSV was writing "Total Oxygen Consumption", let's assume it means consumed.
            # The print statement implies total_oxygen was net, which is confusing.
            # Given the context of the vis tool, focusing on consumption here is cleaner.
            f.write(f"{size},{total_o2_consumption}\n") 
            # The print statement "Average: {total_oxygen/size} kg per person"
            # If total_oxygen was net, this average is also net.
            # If we want avg consumption per person:
            print(f"Colony: {size}, Avg Consumption: {total_o2_consumption/size:.2f} kg per person")
    print("Simulation for CSV complete.")