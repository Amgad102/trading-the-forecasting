import csv
import time
import numpy as np
import sys
import os

# Obtener la ruta absoluta de la carpeta "main"
main_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Agregar "main/" al path si no está ya incluido
if main_path not in sys.path:
    sys.path.append(main_path)
    
from inputs import (
    resource_consumption_power, charge_to_discharge_ratio, storage_capacity, min_power_rps,
    specific_capex_rps, specific_opex_fix_rps, opex_var_rps, start_up_cost_rps, resource_rate_rps,
    fuel_consumption_rate_rps, water_consumption_rate_rps, thermal_power_consumption_rate_rps,
    thermal_power_production_rate_rps, specific_footprint_rps,
    specific_capex_rcs, specific_opex_fix_rcs, opex_var_rcs, start_up_cost_rcs, resource_rate_rcs, min_power_rcs,
    fuel_consumption_rate_rcs, water_consumption_rate_rcs, thermal_power_consumption_rate_rcs,
    thermal_power_production_rate_rcs, specific_footprint_rcs,
    specific_capex_rss, specific_opex_fix_rss, specific_footprint_rss, resource_losses_rss, min_capacity_fraction_rss, rcs_maximum_idle_time, rps_maximum_idle_time, load_factor_rcs,
    bypass_operation_enabled, load_factor_bypass_rcs, resource_rate_bypass_rcs, fuel_consumption_rate_bypass_rcs, water_consumption_rate_bypass_rcs, thermal_power_consumption_rate_bypass_rcs, thermal_power_production_rate_bypass_rcs, opex_var_bypass_rcs,
    resource_rate_bypass_rps, fuel_consumption_rate_bypass_rps, water_consumption_rate_bypass_rps, thermal_power_consumption_rate_bypass_rps, thermal_power_production_rate_bypass_rps, opex_var_bypass_rps, resource_inlet_power_consumption_rate,
    rcs_only_operation_enabled, load_factor_only_rcs, fuel_consumption_rate_only_rcs, water_consumption_rate_only_rcs, thermal_power_consumption_rate_only_rcs, thermal_power_production_rate_only_rcs, opex_var_only_rcs
)

from Mish.utils import get_rate, get_resource_inlet_power_consumption_rate


class RunMain:
    def __init__(self):
        ## Resource Consumption Subsystem:
        self.nominal_power_rcs = resource_consumption_power
        self.min_power_rcs = min_power_rcs*self.nominal_power_rcs
        self.capex_rcs = specific_capex_rcs*self.nominal_power_rcs*1000 ## €
        self.opex_fix_rcs = specific_opex_fix_rcs*self.nominal_power_rcs*1000 ## €/year
        self.opex_var_rcs = opex_var_rcs
        self.start_up_cost_rcs = start_up_cost_rcs
        self.load_factor_rcs = load_factor_rcs
        self.resource_rate_rcs = resource_rate_rcs
        self.fuel_consumption_rate_rcs = fuel_consumption_rate_rcs
        self.water_consumption_rate_rcs = water_consumption_rate_rcs
        self.thermal_power_consumption_rate_rcs = thermal_power_consumption_rate_rcs
        self.thermal_power_production_rate_rcs = thermal_power_production_rate_rcs
        self.footprint_rcs = specific_footprint_rcs*self.nominal_power_rcs ## m2
        self.rcs_maximum_idle_time = rcs_maximum_idle_time
        
        ## Resource Production Subsystem:
        self.nominal_power_rps = self.nominal_power_rcs*charge_to_discharge_ratio/(get_rate(resource_rate_rcs, load_frac = 1, T = 15, RH = 0)*get_rate(resource_rate_rps))
        self.min_power_rps = min_power_rps*self.nominal_power_rps
        self.capex_rps = specific_capex_rps*self.nominal_power_rps*1000 ## €
        self.opex_fix_rps = specific_opex_fix_rps*self.nominal_power_rps*1000 ## €/year
        self.opex_var_rps = opex_var_rps
        self.start_up_cost_rps = start_up_cost_rps
        self.resource_rate_rps = resource_rate_rps
        self.fuel_consumption_rate_rps = fuel_consumption_rate_rps
        self.water_consumption_rate_rps = water_consumption_rate_rps
        self.thermal_power_consumption_rate_rps = thermal_power_consumption_rate_rps
        self.thermal_power_production_rate_rps = thermal_power_production_rate_rps
        self.footprint_rps = specific_footprint_rps*self.nominal_power_rps
        self.rps_maximum_idle_time = rps_maximum_idle_time

        ## Bypass inputs:
        #self.bypass_operation_enabled = True if charge_to_discharge_ratio >= 1 else False
        self. bypass_operation_enabled =  bypass_operation_enabled
        self.min_power_bypass_rcs = self.min_power_rcs
        self.nominal_power_bypass_rcs = self.nominal_power_rcs
        self.load_factor_bypass_rcs = load_factor_bypass_rcs
        self.resource_rate_bypass_rcs = resource_rate_bypass_rcs
        self.fuel_consumption_rate_bypass_rcs = fuel_consumption_rate_bypass_rcs
        self.water_consumption_rate_bypass_rcs = water_consumption_rate_bypass_rcs
        self.thermal_power_consumption_rate_bypass_rcs = thermal_power_consumption_rate_bypass_rcs
        self.thermal_power_production_rate_bypass_rcs = thermal_power_production_rate_bypass_rcs
        self.opex_var_bypass_rcs = opex_var_bypass_rcs
        
        self.min_power_bypass_rps = self.min_power_rps
        self.nominal_power_bypass_rps = self.nominal_power_rcs*charge_to_discharge_ratio/(get_rate(resource_rate_bypass_rcs, load_frac = 1, T = 15, RH = 0)*get_rate(resource_rate_bypass_rps))
        self.resource_rate_bypass_rps = resource_rate_bypass_rps
        self.fuel_consumption_rate_bypass_rps = fuel_consumption_rate_bypass_rps
        self.water_consumption_rate_bypass_rps = water_consumption_rate_bypass_rps
        self.thermal_power_consumption_rate_bypass_rps = thermal_power_consumption_rate_bypass_rps
        self.thermal_power_production_rate_bypass_rps = thermal_power_production_rate_bypass_rps
        self.opex_var_bypass_rps = opex_var_bypass_rps

        ## RCS ONLY:
        self.rcs_only_operation_enabled = rcs_only_operation_enabled
        self.min_power_only_rcs = self.min_power_rcs
        self.nominal_power_only_rcs = self.nominal_power_rcs
        self.load_factor_only_rcs = load_factor_only_rcs
        self.fuel_consumption_rate_only_rcs = fuel_consumption_rate_only_rcs
        self.water_consumption_rate_only_rcs = water_consumption_rate_only_rcs
        self.thermal_power_consumption_rate_only_rcs = thermal_power_consumption_rate_only_rcs
        self.thermal_power_production_rate_only_rcs = thermal_power_production_rate_only_rcs
        self.opex_var_only_rcs = opex_var_bypass_rcs
                
        ## Resource Storage Subsystem:
        
        self.specific_capex_rss = specific_capex_rss
        self.specific_opex_fix_rss = specific_opex_fix_rss  # Cuidado: el nombre repetido "opex_fix_rps"
        self.specific_footprint_rss = specific_footprint_rss  # Cuidado: el nombre repetido "specific_footprint_rps"
        self.resource_losses_rss = resource_losses_rss
        self.resource_inlet_power_consumption_rate = resource_inlet_power_consumption_rate

        # Storage
        if storage_capacity == -1:
            self._storage_capacity = np.inf
            self._storage_capacity_min = 0
        else:
            self._storage_capacity = storage_capacity
            self._storage_capacity_min = self._storage_capacity*min_capacity_fraction_rss
            

    def run(self, purchased_power_list, sold_power_list, resource_inlet_flow_list, resource_inlet_power_consumption_list, resource_outlet_flow_list, temperature_list, relative_humidity_list, tank_start = 0):
        ########### INPUTS ###########
        length = len(purchased_power_list)
        # 
        if not resource_inlet_flow_list:
            resource_inlet_flow_list = [0] * length
        if not resource_outlet_flow_list:
            resource_outlet_flow_list = [0] * length
        # Initialize all lists with zeros of the same length as 'purchased_power_list'
        self._actual_resource_inlet_flow_list = [0]*length
        self._actual_resource_outlet_flow_list = [0]*length
        
        self._electricity_supplied_list = [0] * length
        self._rcs_resource_consumption_list = [0] * length
        self._rcs_fuel_consumption_list = [0] * length
        self._rcs_water_consumption_list = [0]*length
        self._rcs_thermal_power_consumption_list = [0] * length
        self._rcs_thermal_power_production_list = [0]*length
        
        self._electricity_consumption_list = [0] * length
        self._rps_resource_production_list = [0] * length
        self._rps_fuel_consumption_list = [0] * length
        self._rps_water_consumption_list = [0]*length
        self._rps_thermal_power_consumption_list = [0] * length
        self._rps_thermal_power_production_list = [0]*length
        
        self._net_resource_list = [0] * length
        self._fuel_consumption_list = [0]*length
        self._water_consumption_list = [0]*length
        self._thermal_power_consumption_list = [0]*length
        self._thermal_power_production_list = [0]*length
        
        self._rss_level_list = [0] * (len(self._net_resource_list) + 1)
        self._rss_level_list[0] = tank_start  # El primer elemento es el estado inicial del tanque


        def enforce_min_power_during_short_idle(power_list, max_idle_time, min_power):
            forced_idle_mask = [False] * len(power_list)
            
            n = len(power_list)
            i = 0
            while i < n:
                if power_list[i] == 0:
                    # Detectar tramo de ceros
                    start = i
                    while i < n and power_list[i] == 0:
                        i += 1
                    end = i
                    duration = end - start
        
                    # Condición para insertar carga mínima
                    if start > 0 and end < n:
                        if duration < max_idle_time and power_list[start - 1] > 0 and power_list[end] > 0:
                            for j in range(start, end):
                                power_list[j] = min_power
                                forced_idle_mask[j] = True
                else:
                    i += 1
        
            return power_list, forced_idle_mask


        sold_power_list, forced_idle_mask = enforce_min_power_during_short_idle(
                            sold_power_list,
                            self.rcs_maximum_idle_time,
                            self.min_power_rcs
                        )

        purchased_power_list, forced_idle_mask = enforce_min_power_during_short_idle(
                            purchased_power_list,
                            self.rps_maximum_idle_time,
                            self.min_power_rps
                        )

        
        for i in range(0,len(purchased_power_list)):
            purchased_power = purchased_power_list[i]
            sold_power = sold_power_list[i]
            resource_inlet_flow = resource_inlet_flow_list[i]
            resource_inlet_power_consumption = resource_inlet_power_consumption_list[i]
            resource_outlet_flow = resource_outlet_flow_list[i]
            temperature = temperature_list[i]
            relative_humidity = relative_humidity_list[i]
            tank_level_aux = self._rss_level_list[i]
            power_rps = 0
            power_bypass_rps = 0
            power_rcs = 0
            power_bypass_rcs = 0
            resource_rate_flow_rcs = 0
            resource_rate_flow_rps = 0
            resource_rate_flow_bypass = 0 
            rcs_only_flag = 0
            
            ################# RESOURCE FLOWS ########################
            resource_rate_flow_margin_to_max = self._storage_capacity - tank_level_aux
            resource_rate_flow_margin_to_min = tank_level_aux - self._storage_capacity_min
            
            if sold_power > 0 and purchased_power > 0: ## BYPASS ENABLED
                power_rcs = max(min(self.nominal_power_bypass_rcs*get_rate(self.load_factor_bypass_rcs, load_frac =1, T = temperature, RH = relative_humidity), sold_power), self.min_power_bypass_rcs)
                resource_rate_flow_rcs = power_rcs / get_rate(self.resource_rate_bypass_rcs, load_frac = power_rcs/self.nominal_power_bypass_rcs, T = temperature, RH = relative_humidity)
                
                power_rps = max(min(self.nominal_power_bypass_rps, purchased_power), self.min_power_bypass_rps)
                resource_rate_flow_rps = power_rps*self.resource_rate_bypass_rps if self.nominal_power_bypass_rps > 0 else 0
                
                resource_rate_flow_diff = resource_rate_flow_rps - resource_rate_flow_rcs
                if resource_rate_flow_diff > 0:
                    resource_rate_flow_bypass = resource_rate_flow_rcs
                    power_bypass_rcs = power_rcs
                    power_rcs = 0
                    resource_rate_flow_rcs = 0
                    power_bypass_rps = resource_rate_flow_bypass/self.resource_rate_bypass_rps if self.nominal_power_bypass_rps > 0 else 0
                    power_rps= purchased_power - power_bypass_rps
                    resource_rate_flow_rps = power_rps*self.resource_rate_rps if self.nominal_power_rps > 0 else 0
                    if tank_level_aux + resource_rate_flow_rps + resource_inlet_flow - resource_outlet_flow > self._storage_capacity:
                        resource_rate_flow_rps = (self._storage_capacity-tank_level_aux-resource_inlet_flow + resource_outlet_flow)
                        power_rps = resource_rate_flow_rps/self.resource_rate_rps if self.nominal_power_rps > 0 else 0
                else:
                    resource_rate_flow_bypass = resource_rate_flow_rps
                    power_bypass_rps = power_rps
                    power_rps = 0
                    resource_rate_flow_rps = 0
                    power_bypass_rcs = resource_rate_flow_bypass * get_rate(self.resource_rate_bypass_rcs, load_frac = power_rcs/self.nominal_power_bypass_rcs, T = temperature, RH = relative_humidity) 
                    power_rcs = sold_power - power_bypass_rcs
                    if get_rate(self.resource_rate_rcs, load_frac = (power_rcs+power_bypass_rcs)/self.nominal_power_rcs, T = temperature, RH = relative_humidity) != 0:
                        resource_rate_flow_rcs = power_rcs / get_rate(self.resource_rate_rcs, load_frac = (power_rcs+power_bypass_rcs)/self.nominal_power_rcs, T = temperature, RH = relative_humidity)
                    else:
                        resource_rate_flow_rcs = 0
                    #resource_rate_flow_rcs = power_rcs / resource_rate_flow_rcs
                    if tank_level_aux - resource_rate_flow_rcs + resource_inlet_flow - resource_outlet_flow < self._storage_capacity_min:
                        resource_rate_flow_rcs = (tank_level_aux+ resource_inlet_flow - resource_outlet_flow-self._storage_capacity_min)
                        power_rcs = resource_rate_flow_rcs*get_rate(self.resource_rate_rcs, load_frac = (power_rcs+power_bypass_rcs)/self.nominal_power_rcs, T = temperature, RH = relative_humidity)
                    
            elif sold_power > 0:
                power_rcs = self.min_power_rcs*get_rate(self.load_factor_rcs, load_frac =1, T = temperature, RH = relative_humidity)
                if get_rate(self.resource_rate_rcs, load_frac = power_rcs/self.nominal_power_rcs, T = temperature, RH = relative_humidity) != 0:
                    resource_rate_flow_rcs = power_rcs / get_rate(self.resource_rate_rcs, load_frac = power_rcs/self.nominal_power_rcs, T = temperature, RH = relative_humidity)
                else:
                    resource_rate_flow_rcs = 0
                
                # Verifica si la potencia mínima ya excede la capacidad
                if tank_level_aux - resource_rate_flow_rcs + resource_inlet_flow - resource_outlet_flow <= self._storage_capacity_min or sold_power == 0:
                    if self.rcs_only_operation_enabled:
                        power_rcs = max(min(self.nominal_power_only_rcs*get_rate(self.load_factor_only_rcs, load_frac =1, T = temperature, RH = relative_humidity), sold_power), self.min_power_only_rcs)
                        resource_rate_flow_rcs = 0.0
                        rcs_only_flag = 1
                    else:
                        power_rcs = 0.0
                        resource_rate_flow_rcs = 0.0
                else:
                    # Inicializa la potencia con la nominal si es posible
                    power_rcs = max(min(self.nominal_power_rcs*get_rate(self.load_factor_rcs, load_frac =1, T = temperature, RH = relative_humidity), sold_power), self.min_power_rcs)
                    if get_rate(self.resource_rate_rcs, load_frac = power_rcs/self.nominal_power_rcs, T = temperature, RH = relative_humidity) != 0:
                        resource_rate_flow_rcs = power_rcs / get_rate(self.resource_rate_rcs, load_frac = power_rcs/self.nominal_power_rcs, T = temperature, RH = relative_humidity)
                    else:
                        resource_rate_flow_rcs = 0
                    if tank_level_aux - resource_rate_flow_rcs + resource_inlet_flow - resource_outlet_flow < self._storage_capacity_min:
                        resource_rate_flow_rcs = (tank_level_aux+ resource_inlet_flow - resource_outlet_flow-self._storage_capacity_min)
                        power_rcs = resource_rate_flow_rcs*get_rate(self.resource_rate_rcs, load_frac = power_rcs/self.nominal_power_rcs, T = temperature, RH = relative_humidity)
            elif purchased_power > 0:
                power_rps = self.min_power_rps
                resource_rate_flow_rps = power_rps*self.resource_rate_rps
                if tank_level_aux + resource_rate_flow_rps + resource_inlet_flow - resource_outlet_flow > self._storage_capacity or purchased_power == 0:
                    power_rps = 0.0
                    resource_rate_flow_rps = 0.0
                else:
                    # Inicializa la potencia con la nominal si es posible; se le da prioridad al resource_inlet_flow
                    power_rps = max(min(self.nominal_power_rps, purchased_power), self.min_power_rps)
                    resource_rate_flow_rps = power_rps*self.resource_rate_rps
                    if tank_level_aux + resource_rate_flow_rps + resource_inlet_flow - resource_outlet_flow > self._storage_capacity:
                        resource_rate_flow_rps = (self._storage_capacity-tank_level_aux-resource_inlet_flow + resource_outlet_flow)
                        power_rps = resource_rate_flow_rps/self.resource_rate_rps
                        
                power_rps = max(min(self.nominal_power_rps, purchased_power), self.min_power_rps)
                resource_rate_flow_rps = power_rps*self.resource_rate_rps if self.nominal_power_rps > 0 else 0
            
            ################# RESOURCE CONSUMPTION SUBSYSTEM ########################
            water_consumption_rcs = (power_rcs*self.water_consumption_rate_rcs + power_bypass_rcs*self.water_consumption_rate_bypass_rcs)*(1-rcs_only_flag) + rcs_only_flag*power_rcs*self.water_consumption_rate_only_rcs ## Nm3 per hour
            fuel_consumption_rcs = (power_rcs*get_rate(self.fuel_consumption_rate_rcs, load_frac = (power_rcs+power_bypass_rcs)/self.nominal_power_rcs, T = temperature, RH = relative_humidity)+ power_bypass_rcs*get_rate(self.fuel_consumption_rate_bypass_rcs, load_frac = (power_rcs+power_bypass_rcs)/self.nominal_power_bypass_rcs, T = temperature, RH = relative_humidity))*(1-rcs_only_flag) + rcs_only_flag*power_rcs*get_rate(self.fuel_consumption_rate_only_rcs, load_frac = (power_rcs)/self.nominal_power_only_rcs, T = temperature, RH = relative_humidity)  ## MW per hour
            thermal_power_consumption_rcs = (power_rcs*self.thermal_power_consumption_rate_rcs + power_bypass_rcs*self.thermal_power_consumption_rate_bypass_rcs)*(1-rcs_only_flag) + rcs_only_flag*power_rcs*self.thermal_power_consumption_rate_only_rcs ## MW per hour
            thermal_power_production_rcs = (power_rcs*self.thermal_power_production_rate_rcs + power_bypass_rcs*self.thermal_power_production_rate_bypass_rcs)*(1-rcs_only_flag) + rcs_only_flag*power_rcs*self.thermal_power_production_rate_only_rcs ## MW per hour
            ################# RESOURCE PRODUCTION SUBSYSTEM ########################
            water_consumption_rps = power_rps*self.water_consumption_rate_rps + power_bypass_rps*self.water_consumption_rate_bypass_rps ## Nm3 per hour
            fuel_consumption_rps = power_rps*self.fuel_consumption_rate_rps + power_bypass_rps*self.fuel_consumption_rate_bypass_rps ## MW per hour
            thermal_power_consumption_rps = power_rps*self.thermal_power_consumption_rate_rps + power_bypass_rps*self.thermal_power_consumption_rate_bypass_rps ## MW per hour
            thermal_power_production_rps = power_rps*self.thermal_power_production_rate_rps + power_bypass_rps*self.thermal_power_production_rate_bypass_rps ## MW per hour
            
            
            ################# RESOURCE STORAGE SUBSYSTEM ########################
            tank_level_aux += resource_rate_flow_rps - resource_rate_flow_rcs
            if tank_level_aux + resource_inlet_flow - resource_outlet_flow > self._storage_capacity:
                resource_inlet_flow = self._storage_capacity - tank_level_aux + resource_outlet_flow
                tank_level_aux = self._storage_capacity
                resource_inlet_power_consumption = get_resource_inlet_power_consumption_rate(self.resource_inlet_power_consumption_rate, resource_inlet_flow)
            elif tank_level_aux + resource_inlet_flow - resource_outlet_flow < self._storage_capacity_min and resource_outlet_flow > 0:
                resource_outlet_flow = (tank_level_aux-self._storage_capacity_min) + resource_inlet_flow
                tank_level_aux = self._storage_capacity_min
            else:
                tank_level_aux = tank_level_aux + resource_inlet_flow - resource_outlet_flow
           
            
            ######## CREATE LISTS #####################
            self._actual_resource_inlet_flow_list[i] = resource_inlet_flow
            self._actual_resource_outlet_flow_list[i] = resource_outlet_flow
            
            self._electricity_supplied_list[i] = (power_rcs+power_bypass_rcs)
            self._rcs_resource_consumption_list[i] = (resource_rate_flow_rcs)
            self._rcs_fuel_consumption_list[i] = (fuel_consumption_rcs)
            self._rcs_water_consumption_list[i] = (water_consumption_rcs)
            self._rcs_thermal_power_consumption_list[i] = (thermal_power_consumption_rcs)
            self._rcs_thermal_power_production_list[i] = (thermal_power_production_rcs)
            
            self._electricity_consumption_list[i] = (power_rps+power_bypass_rps+resource_inlet_power_consumption)
            self._rps_resource_production_list[i] = (resource_rate_flow_rps)
            self._rps_fuel_consumption_list[i] = (fuel_consumption_rps)
            self._rps_water_consumption_list[i] = (water_consumption_rps)
            self._rps_thermal_power_consumption_list[i] = (thermal_power_consumption_rps)
            self._rps_thermal_power_production_list[i] = (thermal_power_production_rps)
            
            self._net_resource_list[i] = (resource_rate_flow_rps+resource_inlet_flow)-(resource_rate_flow_rcs+resource_outlet_flow)

            # print(f"resource_rate_flow_rps: {resource_rate_flow_rps}")
            # print(f"resource_inlet_flow: {resource_inlet_flow}")
            # print(f"resource_rate_flow_rcs: {resource_rate_flow_rcs}")
            #print(f"net_resource: {(resource_rate_flow_rps+resource_inlet_flow)-(resource_rate_flow_rcs+resource_outlet_flow)}")

            self._fuel_consumption_list[i] = (fuel_consumption_rps+fuel_consumption_rcs)
            self._water_consumption_list[i] = (water_consumption_rps+water_consumption_rcs)
            self._thermal_power_consumption_list[i] = (thermal_power_consumption_rps+thermal_power_consumption_rcs)
            self._thermal_power_production_list[i]= (thermal_power_production_rps+thermal_power_production_rcs)
            
            self._rss_level_list[i+1] = tank_level_aux
 
    
    def get_rps_efficiency(self):
        return self.resource_rate_rps
    
    def get_rcs_efficiency(self):
        return get_rate(resource_rate_rcs, load_frac = 1, T = 15, RH = 0)
    
    def get_bypass_rps_efficiency(self):
        return self.resource_rate_bypass_rps
    
    def get_bypass_rcs_efficiency(self):
        return get_rate(resource_rate_bypass_rcs, load_frac = 1, T = 15, RH = 0)
    
    # def get_rps_efficiency(self):
    #     e_out = self.get_accumulative_rps_resource_production() #kWh/kg h2
    #     e_in = self.get_accumulative_rps_power_consumption() #kWh/kg h2
    #     return e_out / e_in if e_in > 0 else None

    def get_accumulative_rps_resource_production(self):
        return sum(self._rps_resource_production_list)

    def get_accumulative_rps_power_consumption(self):
        return sum(self._electricity_consumption_list)

    # def get_rcs_efficiency(self):
    #     e_out = self.get_accumulative_rcs_power_production()
    #     e_in = self.get_accumulative_rcs_resource_consumption()
    #     return e_out / e_in if e_in > 0 else None
    
    
    def get_accumulative_rcs_resource_consumption(self):
        return sum(self._rcs_resource_consumption_list)

    def get_accumulative_rcs_power_production(self):
        return sum(self._electricity_supplied_list)
    
    def get_fuel_consumption(self):
        return self._fuel_consumption_list
    def get_water_consumption(self):
        return self._water_consumption_list
    def get_fuel_consumption_from_rcs(self):
        return self._rcs_fuel_consumption_list
    def get_water_consumption_from_rcs(self):
        return self._rcs_water_consumption_list
    def get_fuel_consumption_from_rps(self):
        return self._rps_fuel_consumption_list
    def get_water_consumption_from_rps(self):
        return self._rps_water_consumption_list
    def get_thermal_power_consumption(self):
        return self._thermal_power_consumption_list
    def get_thermal_power_production(self):
        return self._thermal_power_production_list
    def get_thermal_power_consumption_from_rps(self):
        return self._rps_thermal_power_consumption_list
    def get_thermal_power_production_from_rps(self):
        return self._rps_thermal_power_production_list
    def get_thermal_power_consumption_from_rcs(self):
        return self._rcs_thermal_power_consumption_list
    def get_thermal_power_production_from_rcs(self):
        return self._rcs_thermal_power_production_list
    def get_rps_opex(self):
        return opex_var_rps
    def get_rcs_opex(self):
        return opex_var_rcs
    
    def get_rss_level_list(self):
        return self._rss_level_list
    def get_electricity_supplied_list(self):
        return self._electricity_supplied_list
    def get_electricity_consumption_list(self):
        return self._electricity_consumption_list
    def get_actual_resource_inlet_flow_list(self):
        return self._actual_resource_inlet_flow_list
    def get_actual_resource_outlet_flow_list(self):
        return self._actual_resource_outlet_flow_list
    def get_capex_rps(self):
        return self.capex_rps
    def get_capex_rcs(self):
        return self.capex_rcs
    def get_footprint_rps(self):
        return self.footprint_rps
    def get_footprint_rcs(self):
        return self.footprint_rcs
    def get_capex_rss(self,storage_capacity):
        return self.specific_capex_rss*storage_capacity
    def get_footprint_rss(self,storage_capacity):
        return self.specific_footprint_rss*storage_capacity
    def get_opex_fix_rss(self,storage_capacity):
        return self.specific_opex_fix_rss*storage_capacity
    def get_footprint(self, storage_capacity):
        return self.get_footprint_rps()+self.get_footprint_rcs()+self.get_footprint_rss(storage_capacity)
    def get_net_resource_list(self):
        return self._net_resource_list
if __name__ == "__main__":
    start_time = time.time()
    RunMain().run()
    end_time = time.time()
    print('Execution time:', end_time-start_time, 'seconds')
