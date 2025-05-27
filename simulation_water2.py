import random
from tkinter import *
from tkinter import ttk # For themed widgets, optional but nice
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# --- Global Simulation Parameters ---
starting_age = 25  # Starting age for beta distribution calculation
individuals_list = [] # Persistent list of individuals in the colony

# --- Helper Function for Water Calculation ---
def calculate_daily_water_for_person(age, body_size, activity_level_today, starting_age_param):
    """
    Calculates daily water consumption for a single person.
    Age and body_size are fixed for the person.
    activity_level_today is the water (L) needed due to activity on a specific day.
    """
    age_factor = 1 / (1 + (age - starting_age_param) * 0.001)
    base_water_for_body = body_size * 0.035  # Liters
    daily_consumption = (base_water_for_body * age_factor) + activity_level_today # Liters
    return daily_consumption

# --- Plotting Function ---
def plot_simulation_data(event=None):
    """
    Generates simulation data based on colony size and plots it.
    - Individuals persist. New ones are added if size increases.
    - Each person has fixed age and gender (body size).
    - Each person has a daily varying activity level affecting water intake.
    - Prints the full current roster to console on each update.
    """
    global ax, canvas, starting_age, status_label, colony_size_scale, individuals_list

    ax.clear()

    try:
        target_colony_size = int(colony_size_scale.get())
        if target_colony_size < 0: # Should not happen with slider min 0
            target_colony_size = 0
            status_label.config(text="Colony size cannot be negative. Set to 0.", style="Orange.TLabel")
        # Slider 'to' value now handles the max, but an internal cap can remain for safety if value is set programmatically.
        # For this setup, with slider max 50, this > 10000 check is unlikely to be hit via UI.
        elif target_colony_size > 50: # Adjusted to reflect new slider max
             target_colony_size = 50
             status_label.config(text="Colony size capped at 50.", style="Orange.TLabel")
             colony_size_scale.set(target_colony_size) # Correct scale if somehow set higher
    except ValueError:
        status_label.config(text="Invalid colony size.", style="Red.TLabel")
        ax.set_title("Mars Colony Water Consumption")
        ax.set_xlabel("Sols (Mars Days)")
        ax.set_ylabel("Total Water Consumption (L/day)")
        ax.grid(True, linestyle='--', alpha=0.7)
        canvas.draw()
        return

    current_actual_size = len(individuals_list)
    action_taken = "No change in size."

    if target_colony_size > current_actual_size:
        action_taken = f"Increased size from {current_actual_size} to {target_colony_size}."
        print(f"\n--- {action_taken} Adding New Individuals: ---")
        for i in range(current_actual_size, target_colony_size):
            is_male = np.random.choice([True, False])
            sex_str = "Male" if is_male else "Female"
            age = np.random.beta(a=2, b=5) * (70 - starting_age) + starting_age
            
            if is_male:
                body_size = np.random.normal(loc=78.0, scale=10.0)
            else:
                body_size = np.random.normal(loc=65.0, scale=9.0)
            body_size = max(20, body_size)

            new_person = {'id': len(individuals_list) + i - current_actual_size, 'age': age, 'sex': sex_str, 'body_size': body_size}
            individuals_list.append(new_person)
    elif target_colony_size < current_actual_size:
        action_taken = f"Decreased size from {current_actual_size} to {target_colony_size}."
        print(f"\n--- {action_taken} Removing Individuals: ---")
        num_to_remove = current_actual_size - target_colony_size
        individuals_list = individuals_list[:target_colony_size]
        print(f"  Removed {num_to_remove} individuals from the end of the list.")
    
    if target_colony_size > 0:
        print(f"\n--- Current Colony Roster (Size: {len(individuals_list)}) ---")
        for idx, person in enumerate(individuals_list):
            print(f"  Person {idx + 1} (Original ID: {person['id']}): Age: {person['age']:.1f} yrs, Sex: {person['sex']}, Body Size: {person['body_size']:.1f} kg")
        print("--- End of Roster ---")
    elif current_actual_size > 0 and target_colony_size == 0:
        print("\n--- Colony size set to 0. Roster cleared. ---")

    if target_colony_size == 0:
        ax.set_title("Mars Colony Water Consumption")
        ax.set_xlabel("Sols (Mars Days)")
        ax.set_ylabel("Total Water Consumption (L/day)")
        ax.text(0.5, 0.5, "Colony size is 0", horizontalalignment='center', verticalalignment='center', transform=ax.transAxes, fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        canvas.draw()
        current_style = status_label.cget("style")
        if current_style != "Orange.TLabel":
             status_label.config(text="Colony size is 0. Nothing to plot.", style="Blue.TLabel")
        return

    sols = 668
    total_colony_consumption_per_sol = np.zeros(sols)

    for sol_index in range(sols):
        daily_total_for_colony_this_sol = 0
        for person in individuals_list: 
            activity_water_today = np.random.normal(loc=1.5, scale=0.5)
            activity_water_today = max(0.25, activity_water_today)

            water_this_person_today = calculate_daily_water_for_person(
                person['age'],
                person['body_size'],
                activity_water_today,
                starting_age
            )
            daily_total_for_colony_this_sol += water_this_person_today
        total_colony_consumption_per_sol[sol_index] = daily_total_for_colony_this_sol
    
    x_values = np.arange(1, sols + 1)
    ax.plot(x_values, total_colony_consumption_per_sol, color="teal", marker='o', linestyle='None', markersize=4, label=f'Total Daily Water ({target_colony_size} people)')
    
    ax.set_title(f"Mars Colony Water Consumption ({target_colony_size} People)", fontsize=14)
    ax.set_xlabel("Sols (Mars Days)", fontsize=12)
    ax.set_ylabel("Total Water Consumption (L/day)", fontsize=12)
    
    ax.legend(loc='best')
    ax.grid(True, linestyle=':', alpha=0.6)
    
    if target_colony_size > 0 and len(total_colony_consumption_per_sol) > 0:
        avg_consumption = np.mean(total_colony_consumption_per_sol)
        min_consumption = np.min(total_colony_consumption_per_sol)
        max_consumption = np.max(total_colony_consumption_per_sol)
        
        stats_text = f"Avg: {avg_consumption:.2f} L/day\nMin: {min_consumption:.2f} L/day\nMax: {max_consumption:.2f} L/day"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=dict(boxstyle='round,pad=0.3', fc='aliceblue', alpha=0.7))

    canvas.draw()
    status_label.config(text=f"Plot updated for {target_colony_size} individuals. Roster printed to console.", style="Green.TLabel")

# Removed update_slider_limit function as it's no longer needed

# --- Main Application Setup ---
if __name__ == "__main__":
    window = Tk()
    window.title("Mars Colony Water Consumption Simulator")
    window.geometry("1000x750") 

    style = ttk.Style()
    try:
        if 'clam' in style.theme_names(): style.theme_use('clam')
        elif 'alt' in style.theme_names(): style.theme_use('alt')
    except TclError: print("Default Tcl theme used.")

    style.configure("Green.TLabel", foreground="green")
    style.configure("Red.TLabel", foreground="red")
    style.configure("Blue.TLabel", foreground="blue")
    style.configure("Orange.TLabel", foreground="orange")
    style.configure("Default.TLabel", foreground="black")

    fig, ax = plt.subplots(figsize=(10, 5.5)) 
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(side=TOP, fill=BOTH, expand=True, pady=(10,0), padx=10)

    control_frame = ttk.Frame(window, padding="10 10 10 10")
    control_frame.pack(side=BOTTOM, fill=X, padx=10, pady=10)

    # Colony Size Slider - Max set to 50
    slider_frame = ttk.LabelFrame(control_frame, text="Colony Size", padding="5")
    slider_frame.pack(side=LEFT, fill=X, expand=True, padx=(0,10))
    
    colony_size_scale = Scale(slider_frame, from_=0, to=50, length=300, orient=HORIZONTAL, command=plot_simulation_data) # Changed 'to' value to 50
    colony_size_scale.set(0) 
    colony_size_scale.pack(side=TOP, fill=X, expand=True, pady=5)

    # Removed the "Adjust Slider Max" limit_frame and its contents

    status_label = ttk.Label(control_frame, text="Adjust colony size using the slider (Max 50).", relief=SUNKEN, anchor=W, padding="2", style="Default.TLabel")
    status_label.pack(side=LEFT, fill=X, expand=True, ipady=2)
    
    window.after(100, lambda: plot_simulation_data()) 

    window.mainloop()
