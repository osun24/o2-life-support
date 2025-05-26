import random
from tkinter import *
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
# def get_user_input():
#     #ts basically just clears everything that isnt an integer so there isnt any errors 
#     while True:
#         try:
#             user_input = float(input("Enter your value here: ")) # mars surface area in solar panels M^2
#             return user_input
#         except ValueError:
#             # status_label.config(text="Please enter a valid number.", fg="red")
#             print("Invalid Input, Please Try Again")
user_input = 0

def plot(var):
    ax.clear()
    global user_input
    user_input = a.get()
    # np.random.normal(loc: center, stdev, size)

    
    x = np.arange(1, 669)  # 668 sols (1 to 668)
    # y = np.arange(0, 1300 * user_input, size=668)
    molar_mass_methane = 16.04  # g/mol
    molar_mass_water = 18.01528
    molar_mass_carbon_dioxide = 44.01 #g/mol

    user_input_float = float(user_input)

    hydrolysis_kWh = random.randint(50, 56) ### in kWh/kg (per kg. of liquid water)
    carbon_dioxide_gatherer = random.uniform(10.7, 106.4) ### in kg/per hour how much carbon can be gathered in an hour
    total_moles_carbon_dioxide = (carbon_dioxide_gatherer*1000)/molar_mass_carbon_dioxide # in g/mol

    total_moles_water = (user_input_float*1000)/molar_mass_water

    # print("Energy needed to enact hydrolysis on " + str(user_input_float) + "Kg  of water = " + str(round(total_energy_hydrolysis, 3)) + " KJ")

    #energy that is needed to turn carbon dioxide and dihydrogen into methane
    total_moles_dihydrogen = total_moles_water
    total_moles_methane = (total_moles_dihydrogen/4) 
    # mass_H2_needed_kg = (4 * molar_mass_hydrogen)/1000
    needed_enthalpy_value = 250 #kJ/mol
 
    max_power_released_methane = 15.4 # KWH/kg
    max_power_released_methane_KJ = max_power_released_methane * 3600 #kJ/kg
    efficiency = np.random.normal(0.33, 0.75, size = 668) #percentage of efficiency of the machine
 # Convert to kg
    
    # Energy (kJ)= Martian_Irradiance × Panel_Area × Panel_Efficiency × Dust_Efficiency × Time
    
                        # the integer in place here should be user_input
    
    y = abs((((((user_input * 1000)/molar_mass_water)/4)*molar_mass_methane)/1000) * max_power_released_methane_KJ * efficiency) # this is the energy output in KJ
    
    print((((((((1 * 1000)/molar_mass_water)/4)*molar_mass_methane)/1000) * max_power_released_methane_KJ * efficiency)))
    '''
    # MAX: 586 * 1 * 0.27 * 0.9 * 88775 * 0.5 * 0.001 = 6320.691225
    # MIN: 586 * 1 * 0.20 * 0.5 * 88775 * 0.5 * 0.001 = 2601.1075
    '''
    ax.clear()
    ax.scatter(x, y, s=20, color="blue", alpha=0.6, label=f'Energy (KJ) : 1300 * {user_input}')# figure out wtf this does #this changes the size of the data points 
    ax.set_title("Mars Energy Plot")
    ax.set_xlabel("Sols (Mars Days)")
    ax.set_ylabel("Energy Output (KJ)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    canvas.draw()
    
    # status_label.config(text=f"Plot updated with multiplier: {a.get()}", fg="green")

def update_limit():
    try:
        new_limit = float(entry.get())
        a.config(to=new_limit)
        plot(None)  # trigger re-plot
    except ValueError:
        status_label.config(text="Please enter a valid number.", fg="red")
# create main window
    
window = Tk()
window.geometry("1000x1400")
window.title("Mars Methane Energy Plotter")

#a = Scale(window, from_=0, to=100, length=400, orient=HORIZONTAL, command = plot)
# b = Label(a, text="Surface in m^2",)
# b.pack()
# user_input = a.get()
# a.pack(ipady=500)

# Create matplotlib figure
fig, ax = plt.subplots(figsize=(10, 6))
canvas = FigureCanvasTkAgg(fig, master=window)
canvas.get_tk_widget().pack(pady=10)

frame = Frame(window)
frame.pack(pady=10)#seperates the distance between the button and the graph

title_label = Label(frame, text="Mars Methane Energy Calculator")
title_label.config(font=("Courier", 24))
title_label.pack(pady=50)

# # Input section

label_frame = Frame(frame, border=False)
label_frame.pack()

input_frame = Frame(frame, border=False)
input_frame.pack()

# random_frame = Frame(frame, border=False)
# random_frame.pack()

plot_button_frame = Frame(frame, border=False)
plot_button_frame.pack()

# Plot button

interactive = NavigationToolbar2Tk(canvas, frame, pack_toolbar=False)
interactive.update()
interactive.pack()

a = Scale(input_frame, from_=0, to=100, length=400, orient=HORIZONTAL, command = plot)
b = Label(label_frame, text="Amount of Methane", font=("Arial", 20))
a.pack(side = "bottom")
b.pack()
user_input = a.get()

plot_button = Button(plot_button_frame, text="Change Limit of Slider (m^2)", command=update_limit, 
                    font=("Arial", 12), bg="lightblue")
plot_button.pack(side=RIGHT, padx=10)

Label(plot_button_frame, text="Amount of Methane:", font=("Arial", 12)).pack(side=LEFT, padx=5)
entry = Entry(plot_button_frame, font=("Arial", 12), width=10)
entry.pack(side=TOP, padx=5)
entry.insert(0, "100")  # Default value        


# Status label
status_label = Label(frame, text="Enter a value and click 'Change Limit (m^2)' to update the plot.", 
                    font=("Arial", 10), fg="blue")
status_label.pack(pady=5)

# Info label
info_label = Label(frame, text="This plots energy output over 668 Mars sols (days)", 
                    font=("Arial", 9), fg="gray")
info_label.pack()

# Initial plot
plot(user_input)  # Initial plot with default value)


window.mainloop()
