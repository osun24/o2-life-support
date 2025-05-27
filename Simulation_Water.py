import random
from tkinter import *
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

colonySize = 0 # people
starting_age = 25
start_size = 59  # in kg
avg_activity = 1.5  # in hours

colony_float = float(colonySize)
total_hours = 1.02749125 * 24
water_intake = 0
daily_consumption = 0

# def water_consumption():
#     activity = np.random.normal(1.5, 0.25, size = 15)
#     is_male = np.random.choice([True, False])
#     water_intake = (body_size * 0.035)
#     water_for_activity = activity # hours of overall activity per day

#     # print("Is male : " + str(is_male))
#     # print("age is : " + str(age) + "/" + str(age_factor)) #years   
#     # print("size is : " + str(body_size) + "/" + str(water_intake)) #kg
#     # print("Activity is : "  + str(activity) + "/" + str(water_for_activity)) #kg

#     if is_male:
#         body_size = np.random.normal(80.3, 9.5, size = 15) # mass (kg)
#     else:
#         body_size = np.random.normal(67.5, 9.4, size = 15) # mass (kg)
        
#     age = np.random.beta(2, 8) * (70 - starting_age) + starting_age
#     age_factor = 1/(1+((age) - starting_age) * 0.001)

#     total_water = (water_intake * age_factor) + water_for_activity # L/day

#     return total_water

def createPerson():
    age = np.random.beta(2, 8, size = 15) * (70 - starting_age) + starting_age
    is_male = np.random.choice([True, False])

    if is_male:
        body_size = np.random.normal(80.3, 9.5, size = 15) # mass (kg)
    else:
        body_size = np.random.normal(67.5, 9.4, size = 15) # mass (kg)

    age_factor = 1/(1+((age) - starting_age) * 0.001)
    water_intake = (body_size * 0.035)

    standardConsumption = (water_intake * age_factor)

    return standardConsumption


peopleList = []
for person in range(colonySize):
    peopleList.append(createPerson())

def activityCalc():
    activity = np.random.normal(1.5, 0.25, size = 15)
    return activity

for person in peopleList:
        peopleList[person] += activityCalc()

print(peopleList)

def plot(var):
    ax.clear()
    global colonySize, daily_consumption
    # daily_consumption = []
    colonySize = a.get()

    # this is a prototype and will be fixed eventually not sure what should be done to make it fixed
    age = np.random.beta(2, 8, size = 15) * (70 - starting_age) + starting_age # skewed towards younger ages
    activity = np.random.normal(1.5, 0.25, size = 15)
    is_male = np.random.choice([True, False])

    # if is_male:
    #     body_size = np.random.normal(80.3, 9.5, size = 15) # mass (kg)
    # else:
    #     body_size = np.random.normal(67.5, 9.4, size = 15) # mass (kg)

    # water_intake = (body_size * 0.035)

    age_factor = 1/(1+((age) - starting_age) * 0.001) # made to 
    water_for_activity = activity # hours of overall activity per day

    is_male = np.random.choice([True, False])

    if is_male:
        body_size = np.random.normal(80.3, 9.5, size = 15) # mass (kg)
    else:
        body_size = np.random.normal(67.5, 9.4, size = 15) # mass (kg)
        
    age = np.random.beta(2, 8, size = 15) * (70 - starting_age) + starting_age
    age_factor = 1/(1+((age) - starting_age) * 0.001)
    # np.random.normal(loc: center, stdev, s   
    
    x = np.arange(1, 16)  # 15 sols (1 to 15)
    ###### y = colonySize * ((body_size * 0.035) * ((1/(1+((age) - starting_age) * 0.001))) + activity)

    y = sum(peopleList)

    # print(((body_size * 0.035) * ((1/(1+((age) - starting_age) * 0.001))) + activity))
    
    # x = np.arrange(1, 669) #15 sols (1 to 15)

    # total_water = (water_intake * age_factor) + water_for_activity
    # for person in range(colonySize):
    #     daily_consumption += water_consumption()

    # for sol in x:
    #     daily_consumption.append(sum([water_consumption() for _ in range(colonySize)]))

    # y =  np.array(water_consumption()) 
    
    '''
    # MAX: 586 * 1 * 0.27 * 0.9 * 88775 * 0.5 * 0.001 = 6320.691225
    # MIN: 586 * 1 * 0.20 * 0.* 88775 * 0.5 * 0.001 = 2601.1075
    '''
    ax.clear()
    ax.scatter(x, y, s=20, color="blue", alpha=0.6, label=f'Energy (KJ) : 1300 * {colonySize}')# figure out wtf this does #this changes the size of the data points 
    ax.set_title("Mars Water Consumption Plot")
    ax.set_xlabel("Sols (Mars Days)")
    ax.set_ylabel("Total Water Consumption")
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


# Create matplotlib figure
fig, ax = plt.subplots(figsize=(10, 6))
canvas = FigureCanvasTkAgg(fig, master=window)
canvas.get_tk_widget().pack(pady=10)

frame = Frame(window)
frame.pack(pady=10)#seperates the distance between the button and the graph

title_label = Label(frame, text="Mars Water Consumption Calculator")
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

a = Scale(input_frame, from_=0, to=50, length=400, orient=HORIZONTAL, command = plot)
a.set(50)
b = Label(label_frame, text="Colony Size ", font=("Arial", 20))
a.pack(side = "bottom")
b.pack()
colonySize = a.get()

plot_button = Button(plot_button_frame, text="Change Limit of Slider (people)", command=update_limit, 
                    font=("Arial", 12), bg="lightblue")
plot_button.pack(side=RIGHT, padx=10)

Label(plot_button_frame, text="Colony Size:", font=("Arial", 12)).pack(side=LEFT, padx=5)
entry = Entry(plot_button_frame, font=("Arial", 12), width=10)
entry.pack(side=TOP, padx=5)
entry.insert(0, "100")  # Default value        

# Status label
status_label = Label(frame, text="Enter a value and click 'Change Limit (People))' to update the plot.", 
                    font=("Arial", 10), fg="blue")
status_label.pack(pady=5)

# Info label
info_label = Label(frame, text="This plots energy output over 15 Mars sols (days)", 
                    font=("Arial", 9), fg="gray")
info_label.pack()

# Initial plot
plot(colonySize)  # Initial plot with default value

window.mainloop()