# from tkinter import *
# import matplotlib.pyplot as plt

# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# fig, ax = plt.subplots()    ``
# window = Tk()
# canvas = FigureCanvasTkAgg(fig, master = window)
# canvas.get_tk_widget().pack()
# window.geometry("1000x1000")
# frame = Frame(window)
# text = Label(frame, text="I hate curry_munchers ")  
# text.config(font=("Courier", 32)) 
# text.pack()
# frame.pack()
# window.title("Solar graph")
# window.mainloop()
#I need you to tell me then
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
    dustEfficiencyVariance = np.random.normal(0.7, 0.2/3, size = 668)
    panelEfficiency = np.random.normal(0.235, (0.27-0.235)/3, size = 668)
    MARTIAN_IRR = 586
    SECONDS = 88775 * 0.5
    
    x = np.arange(1, 669)  # 668 sols (1 to 668)
    # y = np.arange(0, 1300 * user_input, size=668)
    # y = 5350 * user_input * (panelEfficiency * dustEfficiencyVariance)
    
    # Energy (kJ)= Martian_Irradiance × Panel_Area × Panel_Efficiency × Dust_Efficiency × Time
    
                        # the integer in place here should be user_input
    
    y = (MARTIAN_IRR * user_input  * panelEfficiency * dustEfficiencyVariance * SECONDS * 0.001) # convert to kJ
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
window.title("Mars Solar Energy Plotter")

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

title_label = Label(frame, text="Mars Solar Energy Calculator")
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
b = Label(label_frame, text="Surface Area in m^2", font=("Arial", 20))
a.pack(side = "bottom")
b.pack()
user_input = a.get()

plot_button = Button(plot_button_frame, text="Change Limit of Slider (m^2)", command=update_limit, 
                    font=("Arial", 12), bg="lightblue")
plot_button.pack(side=RIGHT, padx=10)

Label(plot_button_frame, text="Surface Area in m^2:", font=("Arial", 12)).pack(side=LEFT, padx=5)
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
plot(user_input)  # Initial plot with default value


window.mainloop()
