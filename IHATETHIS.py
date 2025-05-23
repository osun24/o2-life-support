import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import random

# Function to update scatter plot and slider label
def update_graph(val):
    new_limit = float(val)
    ax.set_ylim(-new_limit, new_limit)  # Adjust y-axis range

    # Generate new random y-values
    y_random = [random.randint(-int(new_limit), int(new_limit)) for _ in x]
    
    # Update scatter plot data
    scatter.set_offsets(np.column_stack((x, y_random)))  
    canvas.draw()

    # Update label to display current y-axis limit
    slider_label.config(text=f"Y-Axis Limit: ±{new_limit}")

# Create Tkinter window
root = tk.Tk()
root.title("Randomized Scatter Plot with Slider-Controlled Y-Axis")

# Create figure and axis
fig, ax = plt.subplots()
x = np.linspace(0, 10, 100)
y = np.sin(x)  # Placeholder

# Create scatter plot (initial empty points)
scatter = ax.scatter(x, y)

ax.set_ylim(-1, 1)  # Initial y-axis limits

# Embed the plot in Tkinter
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

# Create slider label (above the slider)
slider_label = tk.Label(root, text="Y-Axis Limit: ±1")
slider_label.pack()

# Add slider for scaling y-axis
slider = ttk.Scale(root, from_=1, to=10, orient="horizontal", command=update_graph)
slider.pack()

# Run the Tkinter event loop
root.mainloop()

