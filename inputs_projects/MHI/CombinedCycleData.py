import os
import ast
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.interpolate import interp2d


f_J_Wh = 1/3600
LHV_H2 = 120.1E6 #J/kg
LHV_natural_gas = 49.717E6 #J/Kg
#This class is passed as an object to the different classes to obtain the inputs from a file
class CombinedCycleData():
    # def __init__(self, input_filepath):
    #     self.read_data(input_filepath)
    
    def __init__(self, deltat_switch_over = 10, load_switch_over = 30):
        self.gt_option = "59100 kW"
        #self.design_compressor_inlet_temperature = 15 # ISO
        self.deltat_switch_over = deltat_switch_over*60 #from min to second
        self.load_switch_over = load_switch_over #load %
        self.gt_type = "CCGT"
                
        #ISO Performance: 15ºC and 1 atm
        self.gt_dictionary_iso_nominal = {#1. mass kg/s; 2.power W; 3. eff %; 4. Heat Rate kJ/KWh; 5. Exhaust temp;
            "59100 kW": [np.NaN, 59100000, 52.8, 6818.18, np.NaN]
            }
        
        # Factores de corrección por temperatura, humedad y grado de carga. Net power, net Heat Rate y heat consumption:
        net_power_100 = {
            'Temperature': [-5, 5, 15, 25, 35, 45],
            'RH=20%': [1.0548, 1.0172, 0.9754, 0.9227096, 0.8598896, 0.7792346],
            'RH=40%': [1.0549, 1.0171, 0.9741, 0.9189596, 0.8520079, 0.767241],
            'RH=60%': [1.0550, 1.0170, 0.9724, 0.9150031, 0.8443185, 0.7566124],
        }
        
        heat_rate_100 = {
            'Temperature': [-5, 5, 15, 25, 35, 45],
            'RH=20%': [1.0284, 1.0276, 1.0258, 1.028335923, 1.041474512, 1.065635592],
            'RH=40%': [1.0275, 1.0249, 1.0240, 1.03035718, 1.043959638, 1.069626151],
            'RH=60%': [1.0275, 1.0253, 1.0259, 1.035776068, 1.054819325, 1.088589358],
        }
        
        heat_consumption_100 = {
            'Temperature': [-5, 5, 15, 25, 35, 45],
            'RH=20%': [1.083761475, 1.042576783, 0.998806962, 0.950720457, 0.897690011, 0.833489718],
            'RH=40%': [1.083907963, 1.042878938, 0.99937234, 0.951836368, 0.898714415, 0.835210424],
            'RH=60%': [1.084054603, 1.043181902, 0.999938533, 0.952952453, 0.899735885, 0.83693422],
        }

        net_power_80 = {
            'Temperature': [-5, 5, 15, 25, 35, 45],
            'RH=20%': [0.8856, 0.8557, 0.8210, 0.776282663, 0.724480898, 0.657142708],
            'RH=40%': [0.8853, 0.8556, 0.8198, 0.77268773, 0.717315869, 0.646411266],
            'RH=60%': [0.8852, 0.8554, 0.8182, 0.768873201, 0.710425937, 0.63672116],
        }
        
        heat_rate_80 = {
            'Temperature': [-5, 5, 15, 25, 35, 45],
            'RH=20%': [1.0435, 1.0475, 1.0432, 1.046871558, 1.061221136, 1.086934083],
            'RH=40%': [1.0467, 1.0423, 1.0421, 1.048670118, 1.063142223, 1.092199029],
            'RH=60%': [1.0472, 1.0427, 1.0442, 1.054764745, 1.07516205, 1.112678914],
        }
        
        heat_consumption_80 = {
            'Temperature': [-5, 5, 15, 25, 35, 45],
            'RH=20%': [0.926947336, 0.891891487, 0.855555948, 0.814064432, 0.770226233, 0.717730628],
            'RH=40%': [0.927070845, 0.892148909, 0.856037716, 0.815003777, 0.771230801, 0.719248185],
            'RH=60%': [0.927195357, 0.892405978, 0.856520418, 0.815944492, 0.772186164, 0.720769023],
        }
        net_power_60 = {
            'Temperature': [-5, 5, 15, 25, 35, 45],
            'RH=20%': [0.6856, 0.6569, 0.6347, 0.599442804, 0.560049807, 0.511741245],
            'RH=40%': [0.6855, 0.6561, 0.6336, 0.596045439, 0.55338352, 0.502059006],
            'RH=60%': [0.6852, 0.6589, 0.6322, 0.592535599, 0.547114647, 0.493406856],
        }
        
        heat_rate_60 = {
            'Temperature': [-5, 5, 15, 25, 35, 45],
            'RH=20%': [1.0435, 1.1003, 1.1003, 1.103677439, 1.122704434, 1.1543738],
            'RH=40%': [1.0994, 1.1032, 1.0981, 1.107382902, 1.125248785, 1.157031023],
            'RH=60%': [1.0999, 1.1049, 1.1006, 1.114893635, 1.14004617, 1.181682208],
        }
        
        heat_consumption_60 = {
            'Temperature': [-5, 5, 15, 25, 35, 45],
            'RH=20%': [0.753804181, 0.72468079, 0.696985005, 0.663812712, 0.630195365, 0.592100497],
            'RH=40%': [0.753899247, 0.724875867, 0.697351012, 0.664527266, 0.630882762, 0.593274195],
            'RH=60%': [0.753994063, 0.725044272, 0.697716625, 0.665242343, 0.631574814, 0.59444677],
        }
        
        correction_factors_data = {
            'net_power': {
                '100': net_power_100,
                '80': net_power_80,
                '60': net_power_60
            },
            'heat_rate': {
                '100': heat_rate_100,
                '80': heat_rate_80,
                '60': heat_rate_60
            },
            'heat_consumption': {
                '100': heat_consumption_100,
                '80': heat_consumption_80,
                '60': heat_consumption_60
            }
        }
        
        correction_factors = {# interpolators as a function of temperature (ºC) and relative humidity (%)
            'net_power': {
                '100': self.create_interpolator(net_power_100),
                '80': self.create_interpolator(net_power_80),
                '60': self.create_interpolator(net_power_60)
            },
            'heat_rate': {
                '100': self.create_interpolator(heat_rate_100),
                '80': self.create_interpolator(heat_rate_80),
                '60': self.create_interpolator(heat_rate_60)
            },
            'heat_consumption': {
                '100': self.create_interpolator(heat_consumption_100),
                '80': self.create_interpolator(heat_consumption_80),
                '60': self.create_interpolator(heat_consumption_60)
            }
        }        
        self.gt_dictionary_correction_factors = correction_factors
        
        part_load_correction_factor = {# interpolators as a function of load(%), temperature (ºC) and relative humidity (%)
            'net_power': self.create_load_interpolator(correction_factors['net_power']),
            'heat_rate': self.create_load_interpolator(correction_factors['heat_rate']),
            'heat_consumption': self.create_load_interpolator(correction_factors['heat_consumption'])
            }
        self.gt_dictionary_part_load_correction_factors = part_load_correction_factor
        
        
        # Data correction with Compressor Inlet Temperature for H25(32). Assume to apply to all other gas turbines
        self.gt_dictionary_correction_temperature ={# 1. Power (% rated) 2. Heat rate (% rated), 3. Heat Consumption (rated %) 4. mass (rated %), 4. Exhaust temp (ºC) 
            "Power": lambda x: -1.9202E-3*x**2-5.5302E-1*x+1.0879E2,
            "Heat rate": lambda x: 6.8006E-5*x**3+1.9853E-3*x**2+1.1213E-1*x+9.7739E1,
            "Heat consumption": lambda x: -0.3703*x+105.92,
            "Air Flow": lambda x: -5.7381E-4*x**2-2.9419E-1*x+1.0461E2,
            "Exhaust Temperature": lambda x: 0.6286*x-9.4286
            } # x is Temperature in ºC
        self.part_load_performance_curve = [[100,80,60],[100,91,84],[100,85.07,83.21],[0, 20, -57]] #[Load (rated %)] [Efficiency (rated %)] [massflow (rated %)] [Exhaust Temperature (T-T_design) ºC]
        
        self.get_iso_conditions()
        
        # Correct by real conditions and get part-load curve
        #self.get_actual_conditions(self.design_compressor_inlet_temperature)
        
        # Start-up:
        self.gt_dictionary_startup_curve = {
            "time": (5+19.66573)*60, #s
            "Fuel consumption": lambda t: max(0, min(0.1696*(t/60-5)**2 + 1.0389*(t/60-5) + 14.21, 100)) if t >= 5*60 else 0, #(% rated)
            "Load": lambda t: max(0,min(100,10+8.4382*(t/60-9-5))) if t>=(9+5)*60 else 0 #(% rated)
            }
        

        self.calculate_switch_over_iso(self.deltat_switch_over, self.load_switch_over)
        
        # Shut-down:
        self.gt_dictionary_shutdown_curve = {
            "time": 20*60, #s
            "Fuel consumption": lambda t: max(20,30-10/150*t) if t<=4*60 else 0 #(% rated)
            }
    
        self.calculate_shutdown_iso()
        
        
        self.capex = 422.5E6*(self.gt_dictionary_iso_nominal[self.gt_option][1]/650E6)**0.63 # €
        ## MHI-H2
        self.fix_opex = 1.5E6 ## €/y
        self.variable_opex = 0 ## €/kWh
        #self.ramp_up = 3200  ## kW/min
        #self.ramp_down = -6400  ## kW/min

        #self.warm_up_curve = [[0.0,5.0,7.5,8.0,9.0], [13.8,24.9,34.1,28.1,28.1]]  ## [[time (min)] [fuel consumption (% rated)]]
        #self.cool_down_curve = [[0.0,1.9,3.2], [27.9,19.3,18.5]]  ## [[time (min)] [fuel consumption (% rated)]]


    def get_iso_conditions(self):
        turbine_type = self.gt_option
        #temperature = self.design_compressor_inlet_temperature
        # Paso 1: Obtener datos nominales ISO
        mass, power, efficiency, heat_rate, exhaust_temp = self.gt_dictionary_iso_nominal[turbine_type]

        # Paso 2: Aplicar correcciones de temperatura
        corrected_power = power
        corrected_heat_rate = heat_rate
        corrected_efficiency = 1 / corrected_heat_rate * 3600  # Convertir a %

        corrected_mass = mass 
        corrected_exhaust_temp = exhaust_temp

        # Crear el diccionario con condiciones reales
        gt_iso_conditions_dictionary = {
            "Power (W)": corrected_power,
            "Efficiency (%)": corrected_efficiency*100,
            "Heat Rate": corrected_heat_rate,
            "Mass (kg/s)": corrected_mass,
            "Exhaust Temp (ºC)": corrected_exhaust_temp,
        }
        self.gt_dictionary_iso = gt_iso_conditions_dictionary
        return self.gt_dictionary_iso
    
    
    def calculate_switch_over_iso(self, deltat_switch_over, load_switch_over):
        # Paso 1: Encontrar t para el load_switch_over (método numérico o aproximación)
        if load_switch_over < 10:
            load_switch_over = 10
        
        t_switch_over = ((load_switch_over-10)/8.4382+9+5)*60
    
        # Paso 2: Calcular Fuel consumption en t
        fuel_consumption_at_t = self.gt_dictionary_startup_curve["Fuel consumption"](t_switch_over)
        
        # Paso 3: Crear nuevo diccionario
        new_dict = {
            "time": self.gt_dictionary_startup_curve["time"] + deltat_switch_over,
            "Fuel consumption": lambda x: fuel_consumption_at_t if x >= t_switch_over and x < t_switch_over + deltat_switch_over else self.gt_dictionary_startup_curve["Fuel consumption"](x - deltat_switch_over) if x >= t_switch_over + deltat_switch_over else self.gt_dictionary_startup_curve["Fuel consumption"](x),
            "Load": lambda x: load_switch_over if x >= t_switch_over and x < t_switch_over + deltat_switch_over else self.gt_dictionary_startup_curve["Load"](x - deltat_switch_over) if x >= t_switch_over + deltat_switch_over else self.gt_dictionary_startup_curve["Load"](x)
        }

        self.gt_dictionary_load_switch_over = new_dict
        
        # Compute total energy produced and fuel consumption [J] for iso conditions.
        # Integrate from t=0 to t=end
        time_values = np.linspace(0, self.gt_dictionary_load_switch_over["time"], 300)
        dt_power = time_values[1] - time_values[0]
        power_values = [self.gt_dictionary_load_switch_over["Load"](t) for t in time_values]
        W_elec = self.gt_dictionary_iso_nominal[self.gt_option][1]*(40.6/59.1) # During start-up, power produced comes from the GT only
        self.electric_energy_start_up_iso = sum(power_values)/100 * dt_power * W_elec
        
        Q_fuel = self.gt_dictionary_iso_nominal[self.gt_option][1]/(self.gt_dictionary_iso_nominal[self.gt_option][2]/100) #W
        
        # Integrate from t=0 to t = begining of switch over
        time_values_natural_gas = np.linspace(0,t_switch_over,300)
        dt_natural_gas = time_values_natural_gas[1] - time_values_natural_gas[0]
        natural_gas_consumption_values = [self.gt_dictionary_load_switch_over["Fuel consumption"](t) for t in time_values_natural_gas]
        self.natural_gas_energy_consumption_start_up_iso = (sum(natural_gas_consumption_values)/100*dt_natural_gas+deltat_switch_over*fuel_consumption_at_t/100*0.5)*Q_fuel #J
        self.natural_gas_mass_consumption_start_up_iso = self.natural_gas_energy_consumption_start_up_iso/LHV_natural_gas
        
        # Integrate from end of switch over to t = end
        time_values_H2 = np.linspace(t_switch_over+deltat_switch_over,self.gt_dictionary_load_switch_over["time"],300)
        dt_H2 = time_values_H2[1] - time_values_H2[0]
        if dt_H2 <= 0:
            sum_H2_consumption_values = 0
        else:
            H2_consumption_values = [self.gt_dictionary_load_switch_over["Fuel consumption"](t) for t in time_values_H2]
            sum_H2_consumption_values = sum(H2_consumption_values)
        self.H2_energy_consumption_start_up_iso = (sum_H2_consumption_values/100*dt_H2+deltat_switch_over*fuel_consumption_at_t/100*0.5)*Q_fuel #J
        self.H2_mass_consumption_start_up_iso = self.H2_energy_consumption_start_up_iso/LHV_H2 
        
        self.gt_dictionary_start_up_iso = {
            'electric_energy_start_up': self.electric_energy_start_up_iso/1000/3600, #kWh
            'H2_energy_consumption_start_up': self.H2_energy_consumption_start_up_iso/1000/3600, #kWh
            'natural_gas_energy_consumption_start_up': self.natural_gas_energy_consumption_start_up_iso/1000/3600, #kWh
            'H2_mass_consumption_start_up': self.H2_mass_consumption_start_up_iso, #kg
            'natural_gas_mass_consumption_start_up': self.natural_gas_mass_consumption_start_up_iso, #kg
            'time': self.gt_dictionary_load_switch_over["time"] #s
        }

        return self.gt_dictionary_start_up_iso
    
    
    def calculate_shutdown_iso(self):
        time_values_shutdown = np.linspace(0,self.gt_dictionary_shutdown_curve["time"],300)
        dt_shutdown = time_values_shutdown[1] - time_values_shutdown[0]
        H2_consumption_values = [self.gt_dictionary_shutdown_curve["Fuel consumption"](t) for t in time_values_shutdown]
        Q_fuel = self.gt_dictionary_iso_nominal[self.gt_option][1]/(self.gt_dictionary_iso_nominal[self.gt_option][2]/100) #W
        self.H2_energy_consumption_shutdown_iso = sum(H2_consumption_values)/100*dt_shutdown*Q_fuel #J
        self.H2_mass_consumption_shutdown_iso = self.H2_energy_consumption_shutdown_iso/LHV_H2 #kg
        self.gt_dictionary_shutdown_iso = {
            'H2_energy_consumption_shutdown': self.H2_energy_consumption_shutdown_iso, #J
            'H2_mass_consumption_shutdown': self.H2_mass_consumption_shutdown_iso,  #kg
            'time': self.gt_dictionary_shutdown_curve["time"] #s
        }
        return self.gt_dictionary_shutdown_iso
    
        
    def create_interpolator(self, data_dict):
        temperatures = data_dict['Temperature']  # Lista de temperaturas
        rh_values = [20, 40, 60]  # Valores de humedad relativa
    
        # Construir una matriz de puntos de la malla completa para interp2d
        # Necesitas un par de puntos de temperatura y RH para cada valor de tu matriz
        temperature_grid, rh_grid = np.meshgrid(temperatures, rh_values)
    
        # 'values' debe ser una matriz 2D que corresponda al meshgrid
        # Cada columna de 'values' es una serie de datos de temperatura para un valor de RH específico
        values = np.array([data_dict['RH=20%'], data_dict['RH=40%'], data_dict['RH=60%']])
    
        # Crear el interpolador 2D
        interpolator = interp2d(temperature_grid[0], rh_grid[:,0], values, kind='linear', bounds_error=False)
    
        # Lambda que ajusta RH y llama al interpolador
        adjusted_interpolator = lambda temp, rh: interpolator(min(max(temp, -5), 45), min(max(rh, 20), 60))[0]
    
        return adjusted_interpolator
        
    def create_load_interpolator(self, interpolators_at_loads):
        loads = [60, 80, 100]
    
        # Define una función que selecciona el interpolador basado en la carga y llama a este con temp y rh
        def interpolated_value(load, temp, rh):
            if load <= 60:
                return interpolators_at_loads['60'](temp, rh)
            elif load >= 100:
                return interpolators_at_loads['100'](temp, rh)
            else:
                interpolated_values = [interpolators_at_loads[str(load_value)](temp, rh) for load_value in loads]
                load_interpolator = interp1d(loads, interpolated_values, kind='linear', bounds_error=False)
                return load_interpolator(load)
            
        return interpolated_value

            
        
    