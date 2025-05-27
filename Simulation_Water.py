# At the top of your file:
import random
from tkinter import *
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# Your global variables (like starting_age)
starting_age = 25
# ... other global variables ...

print("DEBUG: About to define calculate_fixed_daily_water_for_person") # DEBUG Line 1

# >>>>>>>> THIS FUNCTION DEFINITION MUST COME FIRST <<<<<<<<<<<
def calculate_fixed_daily_water_for_person(age, body_size, activity_level, starting_age_param):
    """
    Calculates the fixed daily water consumption for a single person
    based on their fixed characteristics.
    """
    # print(f"DEBUG: Helper called with age={age}, body_size={body_size}, activity={activity_level}") # Optional detailed debug
    age_factor = 1 / (1 + (age - starting_age_param) * 0.001)
    base_water_for_body = body_size * 0.035
    water_for_activity = activity_level
    daily_consumption = (base_water_for_body * age_factor) + water_for_activity
    return daily_consumption

print("DEBUG: calculate_fixed_daily_water_for_person has been defined.") # DEBUG Line 2

# Other functions you might have (like update_limit) can go here or after plot,
# as long as they are also defined before they are called.

print("DEBUG: About to define plot function") # DEBUG Line 3

# >>>>>>>> THE PLOT FUNCTION DEFINITION COMES AFTER THE HELPER <<<<<<<<<<<
def plot(var):
    print("DEBUG: plot function has been called.") # DEBUG Line 4
    # ... (rest of your plot function as previously provided)
    # Ensure this line (around your line 114) is using the exact same name:
    consumption_this_person = calculate_fixed_daily_water_for_person(
        person_chars['age'],
        person_chars['body_size'],
        person_chars['activity'],
        starting_age
    )
    # ... (rest of your plot function)
    # print("DEBUG: plot function finishing.") # DEBUG Line 5
    return # Make sure your plot function has a return or finishes correctly

print("DEBUG: plot function has been defined.") # DEBUG Line 6

# ... (rest of your Tkinter setup: window, widgets, `a = Scale(...)`, etc.)
# For example:
# window = Tk()
# fig, ax = plt.subplots(...) # ax needs to be defined before plot is called if plot uses it
# canvas = FigureCanvasTkAgg(fig, master=window)
# status_label = Label(...)
# a = Scale(..., command=plot) # 'a' (your scale) needs to be defined before plot is called if plot uses it.
                              # However, the command=plot just registers it.
                              # The actual error is about the helper function.

# initial_plot_value = 0 # Or a.get() if 'a' is defined
# if 'a' in locals() or 'a' in globals(): # Check if 'a' is defined before calling a.get()
#    initial_plot_value = a.get()
# plot(initial_plot_value) # Your initial call to plot

# window.mainloop()