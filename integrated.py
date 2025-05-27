
import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import Slider as MplSlider, Button as MplButton
import random

# Attempt to import from oxygen.py, with placeholders if not found
try:
    from oxygen import Person, oxygen_production
except ImportError:
    print("Warning: 'oxygen.py' not found or 'Person'/'oxygen_production' not defined. Using placeholders.")
    class Person:
        def __init__(self, oxygen_consumption_rate=0.83): # kg/day
            self._oxygen_consumption_rate = oxygen_consumption_rate
        def oxygen_consumption(self):
            return self._oxygen_consumption_rate
    def oxygen_production(algae_area_m2, potato_area_m2):
        o2_from_algae = algae_area_m2 * 0.1 
        o2_from_potatoes = potato_area_m2 * 0.05
        return o2_from_algae + o2_from_potatoes

CO2_PER_O2_MASS_RATIO = 44.0095 / 31.9988

class OxygenVisualizerTab(ttk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.initial_days = 100
        self.max_days = 365
        self.initial_colony_size = 20
        self.initial_algae_area_m2 = 0
        self.max_algae_area_m2 = 12000
        self.initial_potato_area_m2 = 0
        self.max_potato_area_m2 = 8000

        self.current_colony_list = self.generate_new_colony(self.initial_colony_size)
        self.current_colony_actual_size = self.initial_colony_size

        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.sliders = {}
        slider_ax_rects = {
            'colony': [0.15, 0.25, 0.65, 0.03], 'days': [0.15, 0.20, 0.65, 0.03],
            'algae': [0.15, 0.15, 0.65, 0.03], 'potato': [0.15, 0.10, 0.65, 0.03],
            'reset': [0.8, 0.02, 0.1, 0.04]
        }
        self.fig.subplots_adjust(left=0.1, bottom=0.35)

        self.colony_slider_ax = self.fig.add_axes(slider_ax_rects['colony'])
        self.sliders['colony'] = MplSlider(ax=self.colony_slider_ax, label='Colony Size', valmin=10, valmax=50, valinit=self.initial_colony_size, valstep=1)
        self.days_slider_ax = self.fig.add_axes(slider_ax_rects['days'])
        self.sliders['days'] = MplSlider(ax=self.days_slider_ax, label='Sim Days', valmin=30, valmax=self.max_days, valinit=self.initial_days, valstep=1)
        self.algae_area_slider_ax = self.fig.add_axes(slider_ax_rects['algae'])
        self.sliders['algae'] = MplSlider(ax=self.algae_area_slider_ax, label='Algae Area (m²)', valmin=0, valmax=self.max_algae_area_m2, valinit=self.initial_algae_area_m2, valstep=1)
        self.potato_area_slider_ax = self.fig.add_axes(slider_ax_rects['potato'])
        self.sliders['potato'] = MplSlider(ax=self.potato_area_slider_ax, label='Potato Area (m²)', valmin=0, valmax=self.max_potato_area_m2, valinit=self.initial_potato_area_m2, valstep=1)
        self.reset_ax = self.fig.add_axes(slider_ax_rects['reset'])
        self.sliders['reset_button'] = MplButton(self.reset_ax, 'Reset')

        time_points = np.linspace(0, self.initial_days, self.initial_days + 1 if self.initial_days > 0 else 1)
        oxygen_levels, consumption_o2, production_o2, consumption_co2 = self.simulate_oxygen_over_time(
            self.current_colony_list, self.initial_days, self.initial_algae_area_m2, self.initial_potato_area_m2
        )

        self.line, = self.ax.plot(time_points, oxygen_levels, lw=2, label='Oxygen Level (Reserve)')
        self.consumption_line = self.ax.axhline(y=consumption_o2 * 30, color='r', linestyle='--', label=f'O₂ Cons Buffer (30d): {consumption_o2:.2f} kg/d')
        self.production_line = self.ax.axhline(y=production_o2 * 30, color='g', linestyle='--', label=f'O₂ Prod Buffer (30d): {production_o2:.2f} kg/d')
        self.co2_consumption_line = self.ax.axhline(y=consumption_co2 * 30, color='c', linestyle=':', label=f'CO₂ Cons Buffer (30d): {consumption_co2:.2f} kg/d')
        self.balance_line = self.ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)

        net_change_o2 = production_o2 - consumption_o2
        y_pos_net_text_initial = oxygen_levels[-1] * 0.9 if len(oxygen_levels) > 0 and oxygen_levels[-1] is not None and oxygen_levels[-1] > 0 else 10
        self.net_text = self.ax.text(self.initial_days * 0.7, y_pos_net_text_initial, f'Net O₂: {net_change_o2:.2f} kg/d', bbox=dict(facecolor='white', alpha=0.7))

        sustainability_threshold = 1.1
        status, color = "UNSUSTAINABLE (O₂)", "darkred"
        if consumption_o2 > 0 and net_change_o2 > 0 and production_o2 / consumption_o2 >= sustainability_threshold:
            status, color = "SUSTAINABLE (O₂)", "darkgreen"
        elif net_change_o2 > 0:
            status, color = "MARGINAL (O₂)", "darkorange"
        
        y_pos_status_text_initial = oxygen_levels[-1] * 1.1 if len(oxygen_levels) > 0 and oxygen_levels[-1] is not None and oxygen_levels[-1] > 0 else 15
        self.status_text = self.ax.text(self.initial_days * 0.8, y_pos_status_text_initial, status, fontsize=12, fontweight='bold', color=color, bbox=dict(facecolor='white', alpha=0.7))

        self.ax.set_xlabel('Days')
        self.ax.set_ylabel('Gas Level / Buffer (kg)')
        self.ax.set_title(f'O₂ & CO₂ (Colony: {self.current_colony_actual_size}, Days: {self.initial_days}, Algae: {self.initial_algae_area_m2:.0f}m², Potatoes: {self.initial_potato_area_m2:.0f}m²)')
        self.ax.legend(loc='upper left', fontsize='small')
        self.ax.grid(True)

        self.sliders['colony'].on_changed(self.update_plot)
        self.sliders['days'].on_changed(self.update_plot)
        self.sliders['algae'].on_changed(self.update_plot)
        self.sliders['potato'].on_changed(self.update_plot)
        self.sliders['reset_button'].on_clicked(self.reset_plot)
        self.update_plot()

    def generate_new_colony(self, size):
        return [Person() for _ in range(int(size))]

    def simulate_oxygen_over_time(self, people_list, days, total_algae_area_m2, total_potato_area_m2):
        days = int(days)
        daily_consumption_o2 = sum(p.oxygen_consumption() for p in people_list)
        daily_production_o2 = oxygen_production(total_algae_area_m2, total_potato_area_m2)
        daily_consumption_co2 = daily_production_o2 * CO2_PER_O2_MASS_RATIO
        net_oxygen = daily_production_o2 - daily_consumption_o2
        initial_reserve_basis = daily_consumption_o2 if daily_consumption_o2 > 0 else 0.8 * len(people_list)
        initial_oxygen_reserve = initial_reserve_basis * 15
        
        oxygen_levels = [initial_oxygen_reserve]
        if days > 0:
            for day in range(1, days + 1):
                daily_variation = np.random.normal(1.0, 0.02)
                day_change = net_oxygen * daily_variation
                next_level = max(0, oxygen_levels[-1] + day_change if oxygen_levels[-1] is not None else day_change )
                oxygen_levels.append(next_level)
        
        return np.array(oxygen_levels[:days+1] if days > 0 else [initial_oxygen_reserve]), daily_consumption_o2, daily_production_o2, daily_consumption_co2

    def update_plot(self, val=None):
        new_colony_slider_val = int(self.sliders['colony'].val)
        days = int(self.sliders['days'].val)
        algae_area_m2 = float(self.sliders['algae'].val)
        potato_area_m2 = float(self.sliders['potato'].val)

        if new_colony_slider_val != self.current_colony_actual_size:
            self.current_colony_list = self.generate_new_colony(new_colony_slider_val)
            self.current_colony_actual_size = new_colony_slider_val

        current_time_points = np.linspace(0, days, days + 1 if days > 0 else 1)
        oxygen_levels, consumption_o2, production_o2, consumption_co2 = self.simulate_oxygen_over_time(
            self.current_colony_list, days, algae_area_m2, potato_area_m2
        )
        
        safe_oxygen_levels = np.nan_to_num(oxygen_levels, nan=0.0) # Replace NaN with 0 for plotting

        self.line.set_xdata(current_time_points)
        self.line.set_ydata(safe_oxygen_levels)

        self.consumption_line.set_ydata([consumption_o2 * 30, consumption_o2 * 30])
        self.production_line.set_ydata([production_o2 * 30, production_o2 * 30])
        self.co2_consumption_line.set_ydata([consumption_co2 * 30, consumption_co2 * 30])

        net_change_o2 = production_o2 - consumption_o2
        self.consumption_line.set_label(f'O₂ Cons Buffer (30d): {consumption_o2:.2f} kg/d')
        self.production_line.set_label(f'O₂ Prod Buffer (30d): {production_o2:.2f} kg/d')
        self.co2_consumption_line.set_label(f'CO₂ Cons Buffer (30d): {consumption_co2:.2f} kg/d')
        
        current_y_max = self.ax.get_ylim()[1]
        last_o2_level = safe_oxygen_levels[-1] if len(safe_oxygen_levels) > 0 else 0

        y_pos_net_text = last_o2_level * 0.9 if days > 0 and last_o2_level > 0 else current_y_max * 0.1
        x_pos_net_text = days * 0.7 if days > 0 else self.initial_days * 0.7
        y_pos_status_text = last_o2_level * 1.1 if days > 0 and last_o2_level > 0 else current_y_max * 0.15
        x_pos_status_text = days * 0.9 if days > 0 else self.initial_days * 0.8


        self.net_text.set_text(f'Net O₂: {net_change_o2:.2f} kg/d')
        self.net_text.set_position((x_pos_net_text, y_pos_net_text))
        self.net_text.set_bbox(dict(facecolor='lightgreen' if net_change_o2 >=0 else 'lightcoral', alpha=0.7))

        sustainability_threshold = 1.1
        status, color = "UNSUSTAINABLE (O₂)", "darkred"
        if consumption_o2 > 0 and net_change_o2 > 0 and production_o2 / consumption_o2 >= sustainability_threshold:
            status, color = "SUSTAINABLE (O₂)", "darkgreen"
        elif net_change_o2 > 0:
            status, color = "MARGINAL (O₂)", "darkorange"

        self.status_text.set_text(status)
        self.status_text.set_color(color)
        self.status_text.set_bbox(dict(facecolor='white', alpha=0.7))
        self.status_text.set_position((x_pos_status_text, y_pos_status_text))

        self.ax.set_title(f'O₂ & CO₂ (Colony: {self.current_colony_actual_size}, Days: {days}, Algae: {algae_area_m2:.0f}m², Potatoes: {potato_area_m2:.0f}m²)')
        self.ax.set_xlim([0, days if days > 0 else 1])
        
        min_y_val = 0
        all_buffer_values = [0, consumption_o2 * 30, production_o2 * 30, consumption_co2 * 30]
        
        finite_o2_levels = safe_oxygen_levels[np.isfinite(safe_oxygen_levels)]
        if len(finite_o2_levels) > 0:
            min_y_val_o2 = np.min(finite_o2_levels)
            min_y_val = min(min(all_buffer_values), min_y_val_o2 if min_y_val_o2 < 0 else 0)
            current_max_o2 = np.max(finite_o2_levels)
            max_y_val = max(max(all_buffer_values), current_max_o2 if current_max_o2 > 0 else 100)
        else:
            min_y_val = min(all_buffer_values) if all_buffer_values else 0
            max_y_val = max(all_buffer_values) if all_buffer_values and max(all_buffer_values) > 0 else 100

        final_min_y = min_y_val * 1.1 if min_y_val < 0 else min_y_val * 0.9
        if min_y_val == 0: final_min_y = -max_y_val * 0.05 if max_y_val > 0 else -5

        final_max_y = max_y_val * 1.1 if max_y_val > 0 else 100
        if final_min_y >= final_max_y:
            final_max_y = final_min_y + 100

        self.ax.set_ylim([final_min_y, final_max_y])
        self.ax.legend(loc='upper left', fontsize='small')
        self.fig.canvas.draw_idle()

    def reset_plot(self, event=None):
        self.current_colony_list = self.generate_new_colony(self.initial_colony_size)
        self.current_colony_actual_size = self.initial_colony_size
        self.sliders['colony'].reset()
        self.sliders['days'].reset()
        self.sliders['algae'].reset()
        self.sliders['potato'].reset()
        self.update_plot()

# --- Constants for Potatoes/Calories Tab ---
P_POTATO_YIELD_PER_SQ_METER_PER_CYCLE = 5.0; P_CHLORELLA_YIELD_PER_SQ_METER_PER_CYCLE = 0.1
P_POTATO_HARVEST_CYCLE_DAYS = 100; P_CHLORELLA_CYCLE_DAYS = 7
P_AVG_DAILY_POTATO_YIELD_PER_M2 = P_POTATO_YIELD_PER_SQ_METER_PER_CYCLE / P_POTATO_HARVEST_CYCLE_DAYS
P_AVG_DAILY_CHLORELLA_YIELD_PER_M2 = P_CHLORELLA_YIELD_PER_SQ_METER_PER_CYCLE / P_CHLORELLA_CYCLE_DAYS
P_KCAL_PER_KG_POTATO = 770; P_KCAL_PER_KG_CHLORELLA = 3500; P_KCAL_PER_PERSON_PER_DAY = 2000
P_INITIAL_MAX_DAYS = 100; P_INITIAL_POTATO_SPACE_M2 = 150.0
P_INITIAL_CHLORELLA_SPACE_M2 = 50.0; P_INITIAL_NUM_PEOPLE = 4

class PotatoesCaloriesTab(ttk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.fig.subplots_adjust(left=0.1, bottom=0.35, right=0.95, top=0.85) # Adjusted top for text

        days_range_initial = np.array([0, P_INITIAL_MAX_DAYS])
        initial_daily_potato_kcal = P_INITIAL_POTATO_SPACE_M2 * P_AVG_DAILY_POTATO_YIELD_PER_M2 * P_KCAL_PER_KG_POTATO
        initial_daily_chlorella_kcal = P_INITIAL_CHLORELLA_SPACE_M2 * P_AVG_DAILY_CHLORELLA_YIELD_PER_M2 * P_KCAL_PER_KG_CHLORELLA
        initial_daily_demand_kcal = P_INITIAL_NUM_PEOPLE * P_KCAL_PER_PERSON_PER_DAY
        initial_net_daily_kcal_balance = initial_daily_potato_kcal + initial_daily_chlorella_kcal - initial_daily_demand_kcal

        self.line_daily_potato_kcal, = self.ax.plot(days_range_initial, [initial_daily_potato_kcal]*2, label='Daily Potato Calories', color='saddlebrown', lw=2)
        self.line_daily_chlorella_kcal, = self.ax.plot(days_range_initial, [initial_daily_chlorella_kcal]*2, label='Daily Chlorella Calories', color='forestgreen', lw=2)
        self.line_daily_demand_kcal, = self.ax.plot(days_range_initial, [initial_daily_demand_kcal]*2, label='Daily People Demand', color='crimson', ls='--', lw=2)
        self.line_net_daily_calories, = self.ax.plot(days_range_initial, [initial_net_daily_kcal_balance]*2, label='Net Daily Calories', color='blue', ls=':', lw=2.5)

        text_box_props = dict(boxstyle='round,pad=0.3', fc='aliceblue', alpha=0.95, ec='silver')
        self.status_text_props_good = dict(boxstyle='round,pad=0.4', fc='honeydew', alpha=0.95, ec='darkgreen')
        self.status_text_props_bad = dict(boxstyle='round,pad=0.4', fc='mistyrose', alpha=0.95, ec='darkred')
        
        y_text_base, x_text_col1, x_text_col2, x_text_col3 = 0.97, 0.05, 0.35, 0.70 # Adjusted X positions
        self.text_potato_kcal = self.fig.text(x_text_col1, y_text_base, '', fontsize=8, va='top', bbox=text_box_props)
        self.text_chlorella_kcal = self.fig.text(x_text_col1, y_text_base - 0.035, '', fontsize=8, va='top', bbox=text_box_props)
        self.text_space_info = self.fig.text(x_text_col1, y_text_base - 0.07, '', fontsize=8, va='top', bbox=text_box_props)
        self.text_demand_kcal = self.fig.text(x_text_col2, y_text_base, '', fontsize=8, va='top', bbox=text_box_props)
        self.text_people_count_info = self.fig.text(x_text_col2, y_text_base - 0.035, '', fontsize=8, va='top', bbox=text_box_props)
        self.text_net_daily_kcal = self.fig.text(x_text_col2, y_text_base - 0.07, '', fontsize=8, va='top', bbox=text_box_props)
        self.text_overall_status = self.fig.text(x_text_col3, y_text_base, '', fontsize=9, fontweight='bold', va='top')

        self.ax.set_xlabel('Time (Days)', fontsize=12); self.ax.set_ylabel('Daily Calories (kcal/day)', fontsize=12)
        self.ax.set_title('Daily Caloric Production vs. Demand', fontsize=14, y=1.03)
        self.ax.grid(True, which='major', linestyle='--', linewidth=0.5)
        self.ax.legend(loc='lower left', bbox_to_anchor=(0, -0.02), ncol=2, fontsize='small') # Legend position

        self.sliders = {}
        s_rects = {'potato': [0.15,0.25,0.7,0.03],'chlorella': [0.15,0.20,0.7,0.03],'people': [0.15,0.15,0.7,0.03],'days': [0.15,0.10,0.7,0.03]}
        self.sliders['potato'] = MplSlider(ax=self.fig.add_axes(s_rects['potato']), label='Potato Space (m²)', valmin=0, valmax=5000, valinit=P_INITIAL_POTATO_SPACE_M2, valstep=10, color="peru")
        self.sliders['chlorella'] = MplSlider(ax=self.fig.add_axes(s_rects['chlorella']), label='Chlorella Space (m²)', valmin=0, valmax=5000, valinit=P_INITIAL_CHLORELLA_SPACE_M2, valstep=10, color="mediumseagreen")
        self.sliders['people'] = MplSlider(ax=self.fig.add_axes(s_rects['people']), label='Num People', valmin=1, valmax=50, valinit=P_INITIAL_NUM_PEOPLE, valstep=1, color="skyblue")
        self.sliders['days'] = MplSlider(ax=self.fig.add_axes(s_rects['days']), label='Max Graph Days', valmin=30, valmax=1095, valinit=P_INITIAL_MAX_DAYS, valstep=15, color="lightcoral")
        for s in self.sliders.values(): s.on_changed(self.update_plot)
        self.update_plot()

    def update_plot(self, val=None):
        potato_m2, chlorella_m2, num_people, max_days = self.sliders['potato'].val, self.sliders['chlorella'].val, self.sliders['people'].val, int(self.sliders['days'].val)
        self.ax.set_xlim([0, max_days]); days_data = np.array([0, max_days])
        kcal_potato = potato_m2 * P_AVG_DAILY_POTATO_YIELD_PER_M2 * P_KCAL_PER_KG_POTATO
        kcal_chlorella = chlorella_m2 * P_AVG_DAILY_CHLORELLA_YIELD_PER_M2 * P_KCAL_PER_KG_CHLORELLA
        kcal_demand = num_people * P_KCAL_PER_PERSON_PER_DAY
        kcal_net = kcal_potato + kcal_chlorella - kcal_demand

        self.line_daily_potato_kcal.set_data(days_data, [kcal_potato]*2)
        self.line_daily_chlorella_kcal.set_data(days_data, [kcal_chlorella]*2)
        self.line_daily_demand_kcal.set_data(days_data, [kcal_demand]*2)
        self.line_net_daily_calories.set_data(days_data, [kcal_net]*2)

        all_y = [kcal_potato, kcal_chlorella, kcal_demand, kcal_net, 0]
        min_y, max_y = (min(all_y) if all_y else 0), (max(all_y) if all_y else 100)
        pad_upper = (max_y - min_y) * 0.15 or max_y * 0.2 + 100
        pad_lower = (max_y - min_y) * 0.15 or 100
        final_min_y = min(min_y - pad_lower, -pad_lower if min_y > -pad_lower else min_y - pad_lower * 0.1)
        final_max_y = max_y + pad_upper
        if abs(final_max_y - final_min_y) < 500:
            center = (final_max_y + final_min_y) / 2; span = 500
            if min_y < 0 or kcal_net < 0: span = max(500, abs(kcal_net)*2.2, abs(min_y)*2.2); center = 0 if abs(center) < span/4 else center
            final_min_y, final_max_y = center - span / 2, center + span / 2
        self.ax.set_ylim([final_min_y, final_max_y])

        self.text_potato_kcal.set_text(f'Potato Supply: {kcal_potato:,.0f} kcal/d')
        self.text_chlorella_kcal.set_text(f'Chlorella Supply: {kcal_chlorella:,.0f} kcal/d')
        self.text_space_info.set_text(f'Potato: {potato_m2:.0f} m² | Chlorella: {chlorella_m2:.0f} m²')
        self.text_demand_kcal.set_text(f'People Demand: {kcal_demand:,.0f} kcal/d')
        self.text_people_count_info.set_text(f'{int(num_people)} People')
        self.text_net_daily_kcal.set_text(f'Net Balance: {kcal_net:,.0f} kcal/d')
        status_text, status_color, bbox_props = ('Sustainable', 'darkgreen', self.status_text_props_good) if kcal_net >=0 else ('Unsustainable', 'darkred', self.status_text_props_bad)
        self.text_overall_status.set_text(f'Overall System:\n{status_text}'); self.text_overall_status.set_color(status_color); self.text_overall_status.set_bbox(bbox_props)
        self.fig.canvas.draw_idle()

class EnergySimulationTabBase(ttk.Frame):
    def __init__(self, master, title, input_label_text, slider_unit, initial_slider_max=100, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.user_input_var = tk.DoubleVar(value=0)

        self.fig, self.ax = plt.subplots(figsize=(10, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)

        controls_frame = ttk.Frame(self)
        controls_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)
        ttk.Label(controls_frame, text=title, font=("Courier", 16)).pack(pady=10)

        input_controls_frame = ttk.Frame(controls_frame); input_controls_frame.pack(pady=5)
        ttk.Label(input_controls_frame, text=input_label_text, font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        self.slider = tk.Scale(input_controls_frame, from_=0, to=initial_slider_max, length=300, orient=tk.HORIZONTAL, variable=self.user_input_var, command=self.plot_energy)
        self.slider.pack(side=tk.LEFT, padx=5)
        
        limit_frame = ttk.Frame(controls_frame); limit_frame.pack(pady=5)
        ttk.Label(limit_frame, text=f"Set Slider Max ({slider_unit}):", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.entry_limit = ttk.Entry(limit_frame, font=("Arial", 10), width=8); self.entry_limit.pack(side=tk.LEFT, padx=5)
        self.entry_limit.insert(0, str(initial_slider_max))
        ttk.Button(limit_frame, text="Update Limit", command=self.update_limit).pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(controls_frame, text="Adjust slider to see energy output.", font=("Arial", 9)); self.status_label.pack(pady=5)
        self.plot_energy()

    def plot_energy(self, val=None): # To be implemented by subclasses
        raise NotImplementedError

    def update_limit(self):
        try:
            new_limit = float(self.entry_limit.get())
            limit_is_valid = (new_limit > 0) if self.__class__.__name__ != "SabatierEnergyTab" else (new_limit >=0) # Sabatier can be 0
            if limit_is_valid:
                self.slider.config(to=new_limit)
                self.status_label.config(text=f"Slider limit updated to {new_limit:.0f}.", foreground="black")
            else:
                self.status_label.config(text="Limit must be positive (or non-negative for Sabatier).", foreground="red")
        except ValueError:
            self.status_label.config(text="Invalid number for limit.", foreground="red")

class SolarEnergyTab(EnergySimulationTabBase):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, "Mars Solar Energy Calculator", "Surface Area (m²):", "m²", 100, *args, **kwargs)
    def plot_energy(self, val=None):
        self.ax.clear(); current_input = self.user_input_var.get()
        dust_eff = np.random.normal(0.7, 0.2/3, size=668); panel_eff = np.random.normal(0.235, (0.27-0.235)/3, size=668)
        MARTIAN_IRR, SECONDS_HALF_SOL = 586, 88775 * 0.5
        x = np.arange(1, 669)
        y = (MARTIAN_IRR * current_input * panel_eff * dust_eff * SECONDS_HALF_SOL * 0.001) # kJ
        self.ax.scatter(x, y, s=15, color="orange", alpha=0.6, label='Solar Energy (kJ)')
        self.ax.set_title(f"Solar Energy for {current_input:.0f} m² Panels"); self.ax.set_xlabel("Sols (Mars Days)"); self.ax.set_ylabel("Energy Output (kJ)")
        self.ax.legend(); self.ax.grid(True, alpha=0.3); self.canvas.draw()
        self.status_label.config(text=f"Plot updated for {current_input:.0f} m².", foreground="black")

class NuclearEnergyTab(EnergySimulationTabBase):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, "Mars Nuclear Energy Calculator", "Pu-239 Amount (kg):", "kg", 10, *args, **kwargs) # Smaller default max for nuclear
    def plot_energy(self, val=None):
        self.ax.clear(); current_input = self.user_input_var.get()
        BASE_KJ_PER_KG_PER_SOL = 8000 
        efficiency = np.clip(np.random.normal(0.85, 0.05, size=668), 0.7, 0.95)
        x = np.arange(1, 669)
        y = current_input * BASE_KJ_PER_KG_PER_SOL * efficiency # kJ for each sol
        self.ax.scatter(x, y, s=15, color="green", alpha=0.6, label='Nuclear Energy (kJ)')
        self.ax.set_title(f"Nuclear Energy for {current_input:.1f} kg Pu-239"); self.ax.set_xlabel("Sols (Mars Days)"); self.ax.set_ylabel("Energy Output (kJ)")
        self.ax.legend(); self.ax.grid(True, alpha=0.3); self.canvas.draw()
        self.status_label.config(text=f"Plot updated for {current_input:.1f} kg Pu-239.", foreground="black")

class SabatierEnergyTab(EnergySimulationTabBase):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, "Mars Methane (Sabatier) Energy", "Water for Sabatier (kg/sol):", "kg H₂O", 100, *args, **kwargs)
    def plot_energy(self, val=None):
        self.ax.clear(); water_input_kg_per_sol = self.user_input_var.get()
        MOLAR_MASS_CH4, MOLAR_MASS_H2O = 16.04, 18.01528 # g/mol
        # Corrected Sabatier Calculation:
        # CO2 + 4H2 -> CH4 + 2H2O  (Overall reaction for methane production from H2)
        # If water is the source of H2 via electrolysis: 2H2O -> 2H2 + O2
        # So, to get 4 moles of H2, we need 4 moles of H2O (if H2 is directly from H2O splitting for this H2 amount)
        # Or, if we consider the H2O input is for the Sabatier reaction's *water product* side, it's different.
        # Assuming water_input_kg_per_sol is the H2O fed *into electrolysis* to produce H2 for Sabatier.
        
        moles_H2O_input = (water_input_kg_per_sol * 1000) / MOLAR_MASS_H2O # Moles of H2O electrolyzed
        moles_H2_produced = moles_H2O_input * 2 # From 2H2O -> 2H2 + O2 (incorrect, should be 1 H2O -> 1 H2)
                                                # Correct: H2O -> H2 + 1/2 O2. So moles_H2_produced = moles_H2O_input

        moles_H2_produced = (water_input_kg_per_sol * 1000) / MOLAR_MASS_H2O # moles of H2 if 1:1 molar from H2O

        moles_CH4_can_be_produced = moles_H2_produced / 4 # Since 4 moles of H2 are needed for 1 mole of CH4

        mass_CH4_kg = (moles_CH4_can_be_produced * MOLAR_MASS_CH4) / 1000
        
        ENERGY_PER_KG_CH4_KJ = 15.4 * 3600 # kJ/kg (Energy content of CH4)
        
        # Efficiency of the Sabatier reactor and energy conversion
        efficiency_sabatier_conversion = np.clip(np.random.normal(0.50, 0.1, size=668), 0.3, 0.7) # Overall efficiency
        
        x = np.arange(1, 669) # Sols
        daily_energy_kj = mass_CH4_kg * ENERGY_PER_KG_CH4_KJ * efficiency_sabatier_conversion
        
        self.ax.scatter(x, daily_energy_kj, s=15, color="purple", alpha=0.6, label='Sabatier Energy (kJ/sol)')
        self.ax.set_title(f"Sabatier Energy from {water_input_kg_per_sol:.1f} kg H₂O/sol for H₂")
        self.ax.set_xlabel("Sols (Mars Days)"); self.ax.set_ylabel("Energy Output (kJ/sol)")
        self.ax.legend(); self.ax.grid(True, alpha=0.3); self.canvas.draw()
        self.status_label.config(text=f"Plot updated for {water_input_kg_per_sol:.1f} kg H₂O/sol.", foreground="black")


class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Integrated Life Support & Energy Dashboard")
        self.geometry("1000x850") 

        self.notebook = ttk.Notebook(self)
        
        self.oxygen_tab = OxygenVisualizerTab(self.notebook)
        self.notebook.add(self.oxygen_tab, text="O₂ & CO₂ Dynamics")
        
        self.potatoes_tab = PotatoesCaloriesTab(self.notebook)
        self.notebook.add(self.potatoes_tab, text="Caloric Simulation")

        self.solar_tab = SolarEnergyTab(self.notebook)
        self.notebook.add(self.solar_tab, text="Solar Energy")

        self.nuclear_tab = NuclearEnergyTab(self.notebook)
        self.notebook.add(self.nuclear_tab, text="Nuclear Energy")

        self.sabatier_tab = SabatierEnergyTab(self.notebook)
        self.notebook.add(self.sabatier_tab, text="Sabatier Process Energy")

        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()
