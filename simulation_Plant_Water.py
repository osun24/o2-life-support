import random
from tkinter import *
from tkinter import ttk # For themed widgets, optional but nice
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.widgets import Slider
import numpy as np

# https://agrierp.com/blog/watering-potatoes/
# https://hermie.com/en/blog/planting-or-potting-your-own-potatoes#:~:text=Count%20on%20about%205%20tubers,(depending%20on%20the%20variety).
# https://www.gardenary.com/blog/6-easy-steps-to-grow-organic-potatoes

'''
VALUES HERE:
1. How much food per person
    2000 Cal per day
2. How much water for potatoes
    (1-2 inch of water per week)/7 = (0.06926 cups)/7 = 0.0163871/7 = 0.00234101 #L/day
    0.00234101        
    liters per day(1in-2in) = 0.00234101 <-> 0.00468202
    for every tuber(5pot-10pot) 0.01170505 <-> 0.0468202
    for every meter squared(4t-5t) 0.0468202 <-> 0.234101
    
3. How much water for algae
This translates to roughly 1 to 1.5 cubic meters of water per square meter of surface area. 
1000-1500 liters per day. 
4. Inputs
    colony size
    area potatoes
    area algae
5. How much water per person in a day for food (final)
6. how much potatoes are in a square meter 
   4-5 tubers per square meter
   5-10 potatoes per tuber
'''

plt.style.use('seaborn-v0_8-whitegrid')
fig, ax = plt.subplots(figsize=(12, 8.5))
plt.subplots_adjust(left=0.1, bottom=0.42, right=0.75, top=0.82)

# --- Global Simulation Parameters ---
potato_liters_per_day = 0.234101
algae_liters_per_day = 1500/28

INITIAL_MAX_DAYS = 100
INITIAL_POTATO_SPACE_M2 = 150.0
INITIAL_CHLORELLA_SPACE_M2 = 50.0
INITIAL_NUM_PEOPLE = 4

plt.style.use('seaborn-v0_8-whitegrid')
fig, ax = plt.subplots(figsize=(12, 8.5))
plt.subplots_adjust(left=0.1, bottom=0.42, right=0.75, top=0.82)

days_range_initial = np.array([0, INITIAL_MAX_DAYS])

initial_water_potato = INITIAL_POTATO_SPACE_M2 * potato_liters_per_day
initial_water_chlorella = INITIAL_CHLORELLA_SPACE_M2 * algae_liters_per_day
initial_water_total = initial_water_potato + initial_water_chlorella

line_potato, = ax.plot(days_range_initial, [initial_water_potato, initial_water_potato], label='Daily Potato Water', color='saddlebrown', linewidth=2)
line_chlorella, = ax.plot(days_range_initial, [initial_water_chlorella, initial_water_chlorella], label='Daily Chlorella Water', color='forestgreen', linewidth=2)
line_total, = ax.plot(days_range_initial, [initial_water_total, initial_water_total], label='Daily Total', color='crimson', linestyle='--', linewidth=2)

text_box_props = dict(boxstyle='round,pad=0.3', fc='aliceblue', alpha=0.95, ec='silver')
status_text_props_good = dict(boxstyle='round,pad=0.4', fc='honeydew', alpha=0.95, ec='darkgreen')
status_text_props_bad = dict(boxstyle='round,pad=0.4', fc='mistyrose', alpha=0.95, ec='darkred')

y_text_row1 = 0.95
y_text_row2 = 0.90
y_text_row3 = 0.85

x_text_col1 = 0.08
x_text_col2 = 0.60
x_text_col3 = 0.80

text_potato = fig.text(x_text_col1, y_text_row1, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_chlorella = fig.text(x_text_col1, y_text_row2, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_area_info = fig.text(x_text_col1, y_text_row3, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_total = fig.text(x_text_col2, y_text_row1, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_people_count_info = fig.text(x_text_col2, y_text_row2, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_overall_status = fig.text(x_text_col3, y_text_row1, '', fontsize=10, fontweight='bold', verticalalignment='top')

ax.set_xlabel('Time (Days)', fontsize=14)
ax.set_ylabel('Daily Water Consumption (L/day)', fontsize=14, color='black')
ax.tick_params(axis='y', labelcolor='black')
ax.set_title('Daily Water Consumption', fontsize=16, y=1.03)
ax.grid(True, which='major', linestyle='--', linewidth=0.5)

slider_left = 0.15
slider_width = 0.7
slider_height = 0.03
slider_y_start = 0.29
slider_y_spacing = 0.07

ax_potato_area_slider = plt.axes([slider_left, slider_y_start, slider_width, slider_height], facecolor='lightgoldenrodyellow')
potato_area_slider = Slider(ax=ax_potato_area_slider, label='Potato Space (m²)', valmin=0, valmax=5000, valinit=INITIAL_POTATO_SPACE_M2, valstep=10, color="peru")
ax_chlorella_area_slider = plt.axes([slider_left, slider_y_start - slider_y_spacing, slider_width, slider_height], facecolor='lightgoldenrodyellow')
chlorella_area_slider = Slider(ax=ax_chlorella_area_slider, label='Chlorella Space (m²)', valmin=0, valmax=50, valinit=INITIAL_CHLORELLA_SPACE_M2, valstep=1, color="mediumseagreen")
ax_people_slider = plt.axes([slider_left, slider_y_start - 2*slider_y_spacing, slider_width, slider_height], facecolor='lightgoldenrodyellow')
people_slider = Slider(ax=ax_people_slider, label='Number of People', valmin=1, valmax=50, valinit=INITIAL_NUM_PEOPLE, valstep=1, color="skyblue")

def update_daily_rate_plot(val):
    potato_m2 = potato_area_slider.val
    chlorella_m2 = chlorella_area_slider.val
    num_people = people_slider.val
    current_max_days = int(730)

    ax.set_xlim([0, current_max_days])
    days_data_for_lines = np.array([0, current_max_days])

    daily_potato = potato_m2 * potato_liters_per_day * num_people
    daily_chlorella = (chlorella_m2 * algae_liters_per_day) * num_people
    daily_total = daily_potato + daily_chlorella 

    line_potato.set_data(days_data_for_lines, [daily_potato, daily_potato])
    line_chlorella.set_data(days_data_for_lines, [daily_chlorella, daily_chlorella])
    line_total.set_data(days_data_for_lines, [daily_total, daily_total])

    all_y_values = [daily_potato, daily_chlorella, daily_total, 0]
    min_y = min(all_y_values) if all_y_values else 0
    max_y = max(all_y_values) if all_y_values else 100
    
    padding_y_upper = (max_y - min_y) * 0.15 if (max_y - min_y) > 0 else max_y * 0.2 + 100
    padding_y_lower = (max_y - min_y) * 0.15 if (max_y - min_y) > 0 else 100
    final_min_y = min(min_y - padding_y_lower, -padding_y_lower if min_y > -padding_y_lower else min_y - padding_y_lower * 0.1)
    final_max_y = max_y + padding_y_upper
    if abs(final_max_y - final_min_y) < 500:
        center = (final_max_y + final_min_y) / 2
        span_needed = 500
        final_min_y = center - span_needed / 2
        final_max_y = center + span_needed / 2
    ax.set_ylim([final_min_y, final_max_y])

    text_potato.set_text(f'Potato Water Consumption: {daily_potato:,.0f} L/day')
    text_chlorella.set_text(f'Chlorella Water Consumption: {daily_chlorella:,.0f} L/day')
    text_area_info.set_text(f'Potato: {potato_m2:.0f} m² | Chlorella: {chlorella_m2:.0f} m²')
    text_total.set_text(f'Total Water Consumption: {daily_total:,.0f} L/day')
    text_people_count_info.set_text(f'{num_people} People')
        
    fig.canvas.draw_idle()

handles, labels = ax.get_legend_handles_labels()
fig.legend(handles, labels, loc='upper left', bbox_to_anchor=(0.77, 0.80), ncol=1, fontsize=9, title="Daily Rates", title_fontsize=10)

potato_area_slider.on_changed(update_daily_rate_plot)
chlorella_area_slider.on_changed(update_daily_rate_plot)
people_slider.on_changed(update_daily_rate_plot)

update_daily_rate_plot(None)
plt.show()