import random
# import tkinter as tk
from tkinter import *
import matplotlib.pyplot as plt
import numpy as np

# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# def plot():
#     try:
#         user_input = input("Enter your value here: ")
#     except ValueError:
#         status_label.config(text="Please enter a valid number.", fg="red")
#         return

#     x = np.arange(1, sols_in_mars_year +1 )  # 668 sols (1 to 668)
#     y = 1300 * user_input * np.ones_like(x)  # y = constant line

#     ax.clear()
#     ax.scatter(x, y, s=10, color="blue", alpha=0.6, label=f'Energy: 1300 * {user_input}')
#     ax.set_title("Mars Energy Plot")
#     ax.set_xlabel("Sols (Mars Days)")
#     ax.set_ylabel("Energy Output (Wh)")
#     ax.legend()
#     ax.grid(True, alpha=0.3)
#     canvas.draw()

#     status_label.config(text=f"Plot updated with multiplier: {user_input}", fg="green")
   
# window = Tk()
# fig, ax = plt.subplots() 
# canvas = FigureCanvasTkAgg(fig, master = window)
# canvas.get_tk_widget().pack()
# window.geometry("1000x1000")
# frame = Frame(window)
# text = Label(frame, text="I hate curry_munchers ")  
# text.config(font=("Courier", 32)) 
# text.pack()
# frame.pack()
# window.title("Solar graph")
# input_frame = Frame(frame)
# input_frame.pack(pady=10)

# Button(frame, text = "Plot Graph", command = plot).pack(pady =10 )
# status_label = Label(frame, text="Enter a multiplier and click 'Plot Graph'", 
#                     font=("Arial", 10), fg="blue")
# entry = Entry(input_frame, font=("Arial", 12), width=10)
# entry.pack(side=LEFT, padx=5)
# entry.insert(0, "1.0")  # Default value
# window.mainloop()

'''
THINGS TO FIGURE OUT:

    NEEDED : FIND OUT WHAT THE CURRENT TIME OF THE MARS YEAR IS, 

1. How much energy can be produced by solar on mars relative to the area of solar panels
    https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html
    Mars: 586 W/m^2
2. How efficient is it i guess
    https://aurorasolar.com/blog/a-guide-to-solar-panel-efficiency/
3. How much of the surface of the panels can be blocked by dust

No Priority
    4. How do seasons affect this
'''

sols_in_mars_year = 668

solar_irradiance_earth = 1361.0 #W/m^2
solar_irradience_mars = 586.0 #W/m^2
solar_panel_efficiency = round(random.uniform(0.20, 0.27),2) #15-20% efficiency
dust_efficiency = round(random.uniform(0.5, 0.9),2) #10-50% inefficiency

user_input_area = float(input("How many m^2 of solar panels: "))

energy_from_solar = (solar_irradience_mars*user_input_area*0.001*44387*solar_panel_efficiency*dust_efficiency) #kJ/d
print("Energy from solar: " + str(energy_from_solar))