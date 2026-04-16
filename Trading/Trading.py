import pandas as pd
import numpy as np
import time
from MainData.TradingData import TradingData
from Mish.utils import calculate_rss_series
import inputs
    
from inputs import (
    resource_consumption_power, charge_to_discharge_ratio, storage_capacity, min_power_rps,
    specific_capex_rps, specific_opex_fix_rps, opex_var_rps, start_up_cost_rps, resource_rate_rps,
    fuel_consumption_rate_rps, water_consumption_rate_rps, thermal_power_consumption_rate_rps,
    thermal_power_production_rate_rps, specific_footprint_rps,
    specific_capex_rcs, specific_opex_fix_rcs, opex_var_rcs, start_up_cost_rcs, resource_rate_rcs, min_power_rcs,
    fuel_consumption_rate_rcs, water_consumption_rate_rcs, thermal_power_consumption_rate_rcs,
    thermal_power_production_rate_rcs, specific_footprint_rcs,
    specific_capex_rss, specific_opex_fix_rss, specific_footprint_rss, resource_losses_rss, min_capacity_fraction_rss, rcs_maximum_idle_time,
    load_factor_rcs,
    load_factor_bypass_rcs, resource_rate_bypass_rcs, fuel_consumption_rate_bypass_rcs, water_consumption_rate_bypass_rcs, thermal_power_consumption_rate_bypass_rcs, thermal_power_production_rate_bypass_rcs, opex_var_bypass_rcs,
    resource_rate_bypass_rps, fuel_consumption_rate_bypass_rps, water_consumption_rate_bypass_rps, thermal_power_consumption_rate_bypass_rps, thermal_power_production_rate_bypass_rps, opex_var_bypass_rps, resource_inlet_power_consumption_rate
) 

sample_period_days = inputs.sample_period_days

class Trading(object):

    def __init__(self, installed_rcs_power, rcs_total_variable_opex, rcs_bypass_total_variable_opex, installed_rps_power, bypass_operation_enabled, installed_rps_power_bypass, rps_total_variable_opex, rps_bypass_total_variable_opex, rcs_only_operation_enabled, rcs_only_total_variable_opex, rss_day_0=0, rss_capacity=-1):

        self._data_obj = TradingData()
        self._buy_taxes_perc = self._data_obj.buy_taxes_perc
        self._feed_in_supplement = self._data_obj.feed_in_tariff_supplement
        self._feed_in_multiplier = self._data_obj.feed_in_tariff_multiplier

        ## Opex Data
        self._opex_rcs = rcs_total_variable_opex
        self._opex_rps = rps_total_variable_opex
        self._resource_inlet_cost = inputs.resource_inlet_cost # €/unit
        self._opex_bypass_rps = rps_bypass_total_variable_opex
        self._opex_bypass_rcs = rcs_bypass_total_variable_opex
        self._bypass_operation_enabled = bypass_operation_enabled
        ## rss Data
        self._rss_day_0 = rss_day_0
        self._rss_capacity = rss_capacity
        if rss_capacity != -1:
            self._rss_minimum_level = rss_capacity*inputs.min_capacity_fraction_rss
        else:
            self._rss_minimum_level = 0    

        ## Estimate purchase/generation capacity based on P2P systemn to perform trading operations
        self._estimated_purchase_capacity = installed_rps_power
        self._estimated_purchase_capacity_bypass = installed_rps_power_bypass
        self._minimum_purchase_capacity = self._estimated_purchase_capacity * inputs.min_power_rps

        self._estimated_generation_capacity = installed_rcs_power
        self._minimum_generation_capacity = self._estimated_generation_capacity * inputs.min_power_rcs

        ## RCS Only:
        self._rcs_only_operation_enabled = rcs_only_operation_enabled
        self._rcs_only_total_variable_opex = rcs_only_total_variable_opex
        
        ## Initialize variables
        self._electricity_price_df = None

        self._day_count = None
        self._rss_start = None

        self._sample_period_df = None
        self._predicted_operations_df = None
        self._consolidated_operation_df = None

        self._efficiency_rps = None
        self._efficiency_rcs = None
        self._efficiency_p2p_rt = None
        

    def run(self, price_df, resource_input_flow_df, weather_df, day_count, rss_start, efficiency_rps, efficiency_rcs, efficiency_rps_bypass, efficiency_rcs_bypass):
        self._temperature_df = weather_df["Temperature"]
        self._relative_humidity_df = weather_df["Relative Humidity"]
        
        if isinstance(resource_input_flow_df, list) and not resource_input_flow_df:
            length = len(weather_df["Temperature"])
            self._resource_input_flow_df = pd.Series([0.0]*length, index=price_df.index, name='Resource_Available')
            self._resource_input_power_consumption_df = pd.Series([0.0]*length, index=price_df.index, name='Power_Consumption')
        else:
            self._resource_input_flow_df = resource_input_flow_df["Resource_Available"]
            self._resource_input_power_consumption_df = resource_input_flow_df["Power_Consumption"]


        self._electricity_price_df = price_df.assign(Temperature=self._temperature_df, Relative_Humidity=self._relative_humidity_df, Resource_Inlet = self._resource_input_flow_df, Resource_Inlet_Power_Consumption = self._resource_input_power_consumption_df)
        
        self._day_count = day_count
        self._rss_start = rss_start

        #TODO: crear funciones en lugar de constantes
        self._efficiency_rps = efficiency_rps
        self._efficiency_rcs = efficiency_rcs
        self._efficiency_rps_bypass = efficiency_rps_bypass
        self._efficiency_rcs_bypass = efficiency_rcs_bypass
        self._efficiency_p2p_rt = self._efficiency_rcs*self._efficiency_rps
        self._efficiency_p2p_bypass_rt = self._efficiency_rcs_bypass*self._efficiency_rps_bypass
        self._bypass_threshold_ba_cost = self._calculate_threshold_ba_cost() if self._bypass_operation_enabled else 99999
        self._sample_period_df = self._calculate_sample_period_df()
        self._predicted_operations_df, self._predicted_resource_inlet_flow, self._predicted_resource_inlet_power_consumption = self._calculate_predicted_operations_df()
        self._consolidated_operation_df = self._calculate_consolidated_operation_df()
        self._consolidated_resource_inlet_flow = self._calculate_consolidated_resource_inlet_flow()
        self._consolidated_resource_inlet_power_consumption = self._calculate_consolidated_resource_inlet_power_consumption()
        #self._trading_performance = self.calculate_trading_performance()
        
    def get_consolidated_operation_df(self):
        return self._consolidated_operation_df
    
    def get_consolidated_resource_inlet_flow_list(self):
        return self._consolidated_resource_inlet_flow
    
    def get_consolidated_resource_inlet_power_consumption_list(self):
        return self._consolidated_resource_inlet_power_consumption
    
    def get_data_dict(self):
        return {
            'feed_in_supplement': self._feed_in_supplement,
            'feed_in_multiplier': self._feed_in_multiplier,
            'buy_taxes_perc': self._buy_taxes_perc,
        }

    def _calculate_merit_sell_df(self):
        merit_sell_df = self._sample_period_df.copy()
        merit_sell_df['Corrected_Price'] = merit_sell_df['Spot_Price2'] * self._feed_in_multiplier + self._feed_in_supplement
        merit_sell_df = merit_sell_df.sort_values(['Corrected_Price'], ascending=False).reset_index()
        merit_sell_df.loc[:, 'energy_capacity_residual'] = -self._estimated_generation_capacity
        #merit_sell_df.loc[:, 'resource_capacity_residual'] = -self._estimated_generation_capacity / self._efficiency_rcs
        
        def sig(x, n):
            return float(f"{x:.{n}g}")
        
        merit_sell_df.loc[:, 'resource_capacity_residual'] = (
            -self._estimated_generation_capacity / self._efficiency_rcs
        )
        merit_sell_df['resource_capacity_residual'] = merit_sell_df['resource_capacity_residual'].apply(lambda x: sig(x, 5))

        merit_sell_df.loc[:,'type'] = 'sell'
        merit_sell_df[['energy_capacity_residual', 'resource_capacity_residual']] = merit_sell_df[['energy_capacity_residual', 'resource_capacity_residual']].astype(float)

        return merit_sell_df

    def _calculate_merit_buy_df(self):
        #TODO: añadir columna de marginal_cost_buy_bypass
        merit_buy_df = self._sample_period_df.sort_values(['marginal_cost_buy']).reset_index()
        merit_buy_df.loc[:, 'energy_capacity_residual'] = self._estimated_purchase_capacity
        def sig(x, n):
            return float(f"{x:.{n}g}")
        merit_buy_df.loc[:, 'resource_capacity_residual'] = (self._estimated_purchase_capacity * self._efficiency_rps)
        merit_buy_df['resource_capacity_residual'] = merit_buy_df['resource_capacity_residual'].apply(lambda x: sig(x, 5))
        merit_buy_df.loc[:,'type'] = 'buy'
        merit_buy_df[['energy_capacity_residual', 'resource_capacity_residual']] = merit_buy_df[['energy_capacity_residual', 'resource_capacity_residual']].astype(float)
        return merit_buy_df

    def _calculate_merit_accept_df(self):
        merit_accept_df = self._sample_period_df.sort_values(['marginal_cost_accept']).reset_index()
        merit_accept_df.loc[:, 'energy_capacity_residual'] = 0
        merit_accept_df.loc[:, 'resource_capacity_residual'] = merit_accept_df["Resource_Inlet"]
        merit_accept_df.loc[:,'type'] = 'accept'
        merit_accept_df[['energy_capacity_residual', 'resource_capacity_residual']] = merit_accept_df[['energy_capacity_residual', 'resource_capacity_residual']].astype(float)
        return merit_accept_df

    def _calculate_merit_buy_accept_df(self, merit_buy_df, merit_accept_df):
        """
        Processes and merges two merit order DataFrames by:
        1. Creating a 'marginal_cost' column in each DataFrame.
        2. Concatenating both DataFrames.
        3. Sorting by 'marginal_cost' in ascending order.
        
        Parameters:
        merit_buy_df (DataFrame): DataFrame containing buy offers.
        merit_accept_df (DataFrame): DataFrame containing accepted offers.
    
        Returns:
        DataFrame: Processed and merged DataFrame sorted by 'marginal_cost'.
        """
    
        # Step 1: Create 'marginal_cost' column in each DataFrame
        merit_buy_df["marginal_cost"] = merit_buy_df["marginal_cost_buy"]
        merit_buy_df["marginal_cost_bypass"] = merit_buy_df["marginal_cost_buy_bypass"]
        merit_accept_df["marginal_cost"] = merit_accept_df["marginal_cost_accept"]
        merit_accept_df["marginal_cost_bypass"] = merit_accept_df["marginal_cost_accept"]

        
        # Step 2: Concatenate both DataFrames
        merit_buy_accept_df = pd.concat([merit_buy_df, merit_accept_df], ignore_index=True)
    
        # Step 3: Sort by 'marginal_cost' in ascending order
        merit_buy_accept_df = merit_buy_accept_df.sort_values(    by=["marginal_cost", "DateTime"], ascending=[True, True]).reset_index(drop=True)

        # Step 4: Remove rows with resource capacity residual equals to 0
        # merit_buy_accept_df = merit_buy_accept_df[merit_buy_accept_df["resource_capacity_residual"] != 0]
        # merit_buy_accept_df = merit_buy_accept_df.reset_index(drop=True)

        return merit_buy_accept_df


    def _calculate_marginal_cost_resource_inlet(self, df):
        """
        Calculates the marginal cost of accepting the resource based on availability.
    
        Parameters:
        df (DataFrame): DataFrame containing the "Resource_Available" column.
    
        Returns:
        Series: A new column with the calculated marginal cost.
        """
        df["marginal_cost_accept"] = df.apply(lambda row: 99999 if row["Resource_Inlet"] == 0
                                              else self._opex_rcs + ((self._resource_inlet_cost + row["Resource_Inlet_Power_Consumption"] * row["Spot_Price1"] * (1 + self._buy_taxes_perc)/ row["Resource_Inlet"])/ self._efficiency_rcs),
                                              axis=1)

        
        return df["marginal_cost_accept"]


    def _calculate_marginal_cost(self, df):
        #df['Min_Spot_Price'] = df[['Spot_Price1', 'Spot_Price1']].min(axis=1)
        return (df['Spot_Price1'] * (1 + self._buy_taxes_perc) + self._opex_rps) / self._efficiency_p2p_rt  + self._opex_rcs
    
    def _calculate_marginal_cost_bypass(self, df):
        #df['Min_Spot_Price'] = df[['Spot_Price1', 'Spot_Price1']].min(axis=1)
        return (df['Spot_Price1'] * (1 + self._buy_taxes_perc) + self._opex_bypass_rps) / self._efficiency_p2p_bypass_rt  + self._opex_bypass_rcs

    def _calculate_threshold_ba_cost(self):
         num = (
             self._opex_bypass_rps
             - self._efficiency_p2p_bypass_rt * (self._feed_in_supplement - self._opex_bypass_rcs)
         )
         
         den = (
             self._efficiency_p2p_bypass_rt * self._feed_in_multiplier
             - (1 + self._buy_taxes_perc)
         )
         
         return num / den


    def _calculate_sample_period_df(self):
        #TODO: calcular listas de merito a partir de condiciones ambiente -> Se puede hacer internamente en cada una de ellas
        #sample_period_df = self._electricity_price_df[self._electricity_price_df.index < self._day_count * 24 + sample_period_days * 24]
        #sample_period_df = sample_period_df[sample_period_df.index >= self._day_count * 24]
        sample_period_df = self._electricity_price_df
        sample_period_df.loc[:, 'marginal_cost_buy'] = self._calculate_marginal_cost(sample_period_df)
        sample_period_df.loc[:, 'marginal_cost_buy_bypass'] = self._calculate_marginal_cost_bypass(sample_period_df)
        sample_period_df.loc[:,'marginal_cost_accept'] = self._calculate_marginal_cost_resource_inlet(sample_period_df)
        sample_period_df.loc[:, 'marginal_cost_rcs_only'] = self._rcs_only_total_variable_opex if self._rcs_only_operation_enabled else 99999
        
        return sample_period_df

    def _calculate_predicted_operations_df(self):
        merit_buy_df = self._calculate_merit_buy_df()
        merit_accept_df = self._calculate_merit_accept_df()
        merit_sell_df = self._calculate_merit_sell_df()
        transactions_df, consolidated_resource_inlet_flow, consolidated_resource_inlet_power_flow = self._calculate_transaction_df(merit_buy_df, merit_accept_df, merit_sell_df)
        predicted_operations_df = self._sample_period_df.join(transactions_df, how='left').fillna({'energy': 0, 'resource_delta': 0, 'action': 'None', 'energy_sold':0,'energy_purchased':0, 'resource_delta_produced':0,'resource_delta_consumed':0,'action_charging':'None','action_discharging':'None'})
        return predicted_operations_df, consolidated_resource_inlet_flow, consolidated_resource_inlet_power_flow
#        rss_dict, _, _ = self._calculate_rss_data_tuple(operations_df, rss_start)
#        return operations_df.join(pd.Series(rss_dict, name='rss'), how='left')

    def _calculate_consolidated_operation_df(self):
        return self._predicted_operations_df.loc[(self._day_count * 24):((self._day_count + 1) * 24 - 1), :]
    def _calculate_consolidated_resource_inlet_flow(self):
        """
        Extracts a 24-hour period from self._consolidated_resource_inlet_flow
        based on self._day_count.
        
        Returns:
            list: A sublist corresponding to a single day (24 values).
        """
        start_idx = self._day_count * 24
        end_idx = (self._day_count + 1) * 24
        
        return self._predicted_resource_inlet_flow[start_idx:end_idx]

    def _calculate_consolidated_resource_inlet_power_consumption(self):
        start_idx = self._day_count * 24
        end_idx = (self._day_count + 1) * 24
        
        return self._predicted_resource_inlet_power_consumption[start_idx:end_idx]

    def _calculate_transaction_df(self, merit_buy_df, merit_accept_df, merit_sell_df):
        rss_residual = self._rss_start
        self.EPS = 0.001*self._rss_capacity if self._rss_capacity != -1 else 0.001*self._estimated_generation_capacity / self._efficiency_rcs
        i = 0
        transactions_dict, i = self._calculate_transaction({}, i, 0, 0,0,'None')

        transaction_bool = True

        merit_buy_accept_df = self._calculate_merit_buy_accept_df(merit_buy_df, merit_accept_df)
        N = len(self._electricity_price_df)
        self._rss_current = np.full(N, self._rss_start, dtype=float)
        self._rss_global_max = self._rss_start
        start = self._electricity_price_df.index.min()
        
        sell_idx   = merit_sell_df['index'].to_numpy()
        ba_idx   = merit_buy_accept_df['index'].to_numpy()
        
        sell_active = np.ones(len(sell_idx), dtype=bool)
        ba_active = np.ones(len(ba_idx), dtype=bool)
        
        sell_price = merit_sell_df['Corrected_Price'].to_numpy(dtype=np.float64, copy=False)
        ba_cost    = merit_buy_accept_df['marginal_cost'].to_numpy(dtype=np.float64, copy=False)
        ba_cost_bypass = merit_buy_accept_df['marginal_cost_bypass'].to_numpy(dtype=np.float64, copy=False)
        
        #TODO: añadir lista con costes marginales de bypass, ¿tiene longitud N (no 2N)?

        length_ba = len(merit_buy_accept_df['marginal_cost'])
        length_sell = len(merit_sell_df['Corrected_Price'])
        
        sell_res = merit_sell_df['resource_capacity_residual'].to_numpy(dtype=np.float64, copy=False)
        ba_res= merit_buy_accept_df['resource_capacity_residual'].to_numpy(dtype=np.float64, copy=False)
        
        sell_energy = merit_sell_df['energy_capacity_residual'].to_numpy(dtype=np.float64, copy=False)
        ba_energy = merit_buy_accept_df['energy_capacity_residual'].to_numpy(dtype=np.float64, copy=False)
        
        #   is_buy[k] == True  -> 'buy'
        #   is_buy[k] == False -> 'accept'
        ba_is_buy = (merit_buy_accept_df['type'].to_numpy(copy=False) == 'buy')
        
        if self._rcs_only_operation_enabled is True:
            k = 0
            while k < length_ba:
                if ba_cost[k] >  self._rcs_only_total_variable_opex:
                    ba_active[k] = False
                k+=1
        # if self._bypass_operation_enabled is True:
        #     k = 0
        #     while k < length_ba:
        #         if ba_cost[k] >=  self._bypass_threshold_ba_cost:
        #             ba_active[k] = False
        #         k+=1        
        
        while transaction_bool: 
            k = 0 #loop in the order of buy_accept (lower marginal cost, earlier events)
            while k < length_ba and not ba_active[k]:
                k+=1
            transaction_bool = False
            

            while not transaction_bool and k < length_ba:
                j = 0 #loop in the order of sell (higher selling price)
                while j < length_sell and not sell_active[j]:
                    j+=1

                ## Break cycle if there is not possible transaction (check the best case scenario - if it exists
                #if (j==length_sell or (sell_price[j] < ba_cost[k] and rss_residual <= 0)):
                    #break

                if j == length_sell:
                    break

                while not transaction_bool and j < length_sell:

                    if rss_residual > self._rss_minimum_level and rss_residual*self._efficiency_rcs > self._minimum_generation_capacity and sell_price[j]>=self._opex_rcs:
                    #if rss_residual > self._rss_minimum_level and rss_residual*self._efficiency_rcs > self._minimum_generation_capacity and sell_price[j] >= merit_buy_accept_df['marginal_cost'].min(): # There is resource at the beggining
                        sell_index = sell_idx[j]
                        if rss_residual > abs(merit_sell_df['resource_capacity_residual'][j]):
                            resource_capacity_delta = abs(merit_sell_df['resource_capacity_residual'][j])
                            energy_capacity_delta = abs(merit_sell_df['energy_capacity_residual'][j])
                            transactions_dict, i = self._calculate_transaction(transactions_dict, i,
                                                                               sell_index, -energy_capacity_delta,
                                                                               -resource_capacity_delta,
                                                                               'sell')
                            sell_active[j] = False
                            rss_residual -= resource_capacity_delta
                            if rss_residual <= self.EPS:
                                rss_residual = 0

                            transaction_bool = True
                            self._rss_current[sell_index-start:] -= resource_capacity_delta

                        elif abs(merit_sell_df['energy_capacity_residual'][j]) > self._minimum_generation_capacity:
                            resource_capacity_delta = rss_residual
                            energy_capacity_delta = resource_capacity_delta * self._efficiency_rcs ##FIXME
                            transactions_dict, i = self._calculate_transaction(transactions_dict, i,
                                                                               sell_index, -energy_capacity_delta,
                                                                               -resource_capacity_delta,
                                                                               'sell')
                            sell_res[j] += resource_capacity_delta
                            sell_energy[j] += energy_capacity_delta
                            if sell_res[j] >= -self.EPS:
                                sell_active[j] = False
                                
                            rss_residual = 0
                            transaction_bool = True
                            self._rss_current[sell_index-start:] -= resource_capacity_delta
                        
                        
                    elif sell_price[j] > ba_cost[k] and sell_idx[j] >= ba_idx[k]: ## sell_idx[j] > ba_idx[k]

                        if (not self._bypass_operation_enabled) or (ba_cost[k]<ba_cost_bypass[ba_idx.tolist().index(sell_idx[j])]):

                        # if (not self._bypass_operation_enabled) \
                        #    or (sell_idx[j] > ba_idx[k] and ba_cost[k] < self._bypass_threshold_ba_cost) \
                        #    or (sell_idx[j] == ba_idx[k] and self._bypass_operation_enabled and ba_cost[k] < self._bypass_threshold_ba_cost):
                            # aceptar la venta
                            buy_index = ba_idx[k]
                            sell_index = sell_idx[j]
                            resource_capacity_delta = min(merit_buy_accept_df['resource_capacity_residual'][k], -merit_sell_df['resource_capacity_residual'][j])
                            if self._rss_capacity != -1 and len(transactions_dict) > 1:  ## avoid significant computational effort if there is not a set maximum capacity
                                b = buy_index - start
                                s = sell_index - start
                                if s > b:
                                    interval_max = self._rss_current[b:s].max()
                                elif s == b:
                                    interval_max = self._rss_current[b] - resource_capacity_delta
    
                                rss_series_aux_max = max(self._rss_global_max, interval_max + resource_capacity_delta)
    
                                resource_capacity_delta = min(resource_capacity_delta, (self._rss_capacity - rss_series_aux_max+resource_capacity_delta))
                                if resource_capacity_delta > self.EPS:
                                    is_storage_capacity_below_maximum = True
                                else:
                                    is_storage_capacity_below_maximum = False
                                #is_storage_capacity_below_maximum = rss_series_aux.max() <= self._rss_capacity
                            else:
                                is_storage_capacity_below_maximum = True
    
                            #resource_capacity_delta = min(merit_buy_accept_df['resource_capacity_residual'][k], resource_capacity_delta_max)
                            buy_accept_type =  'buy' if ba_is_buy[k] else 'accept'
                            
                            if buy_accept_type == 'buy':
                                energy_capacity_delta_buy = resource_capacity_delta / self._efficiency_rps
                            else:
                                energy_capacity_delta_buy = 0
                            energy_capacity_delta_sell = resource_capacity_delta * self._efficiency_rcs
                            # Check if storage capacity is exceeded after transaction
    
                                
                            if self._rss_capacity == -1 or is_storage_capacity_below_maximum:
                                transactions_dict, i = self._calculate_transaction(transactions_dict, i,
                                                                                   buy_index, energy_capacity_delta_buy,
                                                                                   resource_capacity_delta,
                                                                                   buy_accept_type)
    
                                transactions_dict, i = self._calculate_transaction(transactions_dict, i,
                                                                                   sell_index, -energy_capacity_delta_sell,
                                                                                   -resource_capacity_delta,
                                                                                   'sell')
    
                                # Actualizar los valores del elemento en la lista de mérito
                                ba_res[k] -= resource_capacity_delta
                                ba_energy[k] -= energy_capacity_delta_buy
                                
                                # Si el recurso disponible se ha agotado, eliminar la fila
                                if ba_res[k] <= self.EPS:
                                    ba_active[k] = False
                                
                                sell_res[j] += resource_capacity_delta
                                sell_energy[j] += energy_capacity_delta_sell
                                if sell_res[j] >= -self.EPS:
                                    sell_active[j] = False
                                    
                                    
                                transaction_bool = True
                                offset = buy_index-start
                                self._rss_current[offset: sell_index - start] += resource_capacity_delta
                                self._rss_global_max = self._rss_current.max()
                       
                            
                    # elif sell_price[j] > ba_cost_bypass[k] and sell_idx[j] == ba_idx[k]:
                    #     buy_index = ba_idx[k]
                    #     sell_index = sell_idx[j]
                    #     resource_capacity_delta = min(merit_buy_accept_df['resource_capacity_residual'][k], -merit_sell_df['resource_capacity_residual'][j])
                    #     if self._rss_capacity != -1 and len(transactions_dict) > 1:  ## avoid significant computational effort if there is not a set maximum capacity
                    #         b = buy_index - start
                    #         s = sell_index - start
                    #         if s > b:
                    #             interval_max = self._rss_current[b:s].max()
                    #         elif s == b:
                    #             interval_max = self._rss_current[b] - resource_capacity_delta

                    #         rss_series_aux_max = max(self._rss_global_max, interval_max + resource_capacity_delta)

                    #         resource_capacity_delta = min(resource_capacity_delta, (self._rss_capacity - rss_series_aux_max+resource_capacity_delta))
                    #         if resource_capacity_delta > self.EPS:
                    #             is_storage_capacity_below_maximum = True
                    #         else:
                    #             is_storage_capacity_below_maximum = False
                    #         #is_storage_capacity_below_maximum = rss_series_aux.max() <= self._rss_capacity
                    #     else:
                    #         is_storage_capacity_below_maximum = True

                    #     #resource_capacity_delta = min(merit_buy_accept_df['resource_capacity_residual'][k], resource_capacity_delta_max)
                    #     buy_accept_type =  'buy' if ba_is_buy[k] else 'accept'
                        
                    #     if buy_accept_type == 'buy':
                    #         energy_capacity_delta_buy = resource_capacity_delta / self._efficiency_rps_bypass
                    #     else:
                    #         energy_capacity_delta_buy = 0
                    #     energy_capacity_delta_sell = resource_capacity_delta * self._efficiency_rcs_bypass
                    #     # Check if storage capacity is exceeded after transaction

                            
                    #     if self._rss_capacity == -1 or is_storage_capacity_below_maximum:
                    #         transactions_dict, i = self._calculate_transaction(transactions_dict, i,
                    #                                                             buy_index, energy_capacity_delta_buy,
                    #                                                             resource_capacity_delta,
                    #                                                             '')

                    #         transactions_dict, i = self._calculate_transaction(transactions_dict, i,
                    #                                                             sell_index, -energy_capacity_delta_sell,
                    #                                                             -resource_capacity_delta,
                    #                                                             'bypass')

                    #         # Actualizar los valores del elemento en la lista de mérito
                    #         ba_res[k] -= resource_capacity_delta
                    #         ba_energy[k] -= energy_capacity_delta_buy
                            
                    #         # Si el recurso disponible se ha agotado, eliminar la fila
                    #         if ba_res[k] <= self.EPS:
                    #             ba_active[k] = False
                            
                    #         sell_res[j] += resource_capacity_delta
                    #         sell_energy[j] += energy_capacity_delta_sell
                    #         if sell_res[j] >= -self.EPS:
                    #             sell_active[j] = False
                                
                                
                    #         transaction_bool = True
                    #         offset = buy_index-start
                    #         self._rss_current[offset: sell_index - start] += resource_capacity_delta
                    #         self._rss_global_max = self._rss_current.max()
                        
                    elif sell_price[j] > ba_cost[k] and sell_idx[j] < ba_idx[k]:
                        if (not self._bypass_operation_enabled) or (ba_cost[k]<ba_cost_bypass[ba_idx.tolist().index(sell_idx[j])]):

                            # Search if previous transactions can be permutated to enable this operation
                            buy_index = ba_idx[k]
                            sell_index = sell_idx[j]
                            resource_capacity_delta = min(merit_buy_accept_df['resource_capacity_residual'][k], -merit_sell_df['resource_capacity_residual'][j])
                            if self._rss_capacity != -1 and len(transactions_dict) > 1:  ## avoid significant computational effort if there is not a set maximum capacity
                                b = buy_index - start
                                s = sell_index - start
                                
                                # máximo fuera del intervalo [s:b)
                                left_max  = self._rss_current[:s].max() if s > 0 else float('-inf')
                                right_max = self._rss_current[b:].max() if b < len(self._rss_current) else float('-inf')
                                outside_max = max(left_max, right_max)
                            
                                inside_max = self._rss_current[s:b].max()
                            
                                inside_new_max = inside_max - resource_capacity_delta
                                
                                rss_series_aux_max = max(outside_max, inside_new_max)
                                
                                resource_capacity_delta = min(resource_capacity_delta, (self._rss_capacity - rss_series_aux_max+resource_capacity_delta))
                                if resource_capacity_delta > self.EPS:
                                    is_storage_capacity_below_maximum = True
                                else:
                                    is_storage_capacity_below_maximum = False
                                #is_storage_capacity_below_maximum = rss_series_aux.max() <= self._rss_capacity
                            else:
                                is_storage_capacity_below_maximum = True
                            t, using_storage  = self.find_permutation_candidate(transactions_dict, buy_index, sell_index)
                            
                            if t is not None:
                                #resource_capacity_delta = min(merit_buy_accept_df['resource_capacity_residual'][k], resource_capacity_delta_max)
                                buy_accept_type =  'buy' if ba_is_buy[k] else 'accept'
                                if buy_accept_type == 'buy':
                                    energy_capacity_delta_buy = resource_capacity_delta / self._efficiency_rps
                                else:
                                    energy_capacity_delta_buy = 0
                                energy_capacity_delta_sell = resource_capacity_delta * self._efficiency_rcs
    
                                if self._rss_capacity == -1  or is_storage_capacity_below_maximum:
                                    
                                    if using_storage == False:
                                        transactions_dict, i, resource_capacity_delta_traded = self.permute_transactions(transactions_dict, i, buy_index, energy_capacity_delta_buy, resource_capacity_delta, buy_accept_type, 
                                                                  sell_index, energy_capacity_delta_sell, t)
                                    else:
                                        transactions_dict, i, resource_capacity_delta_traded = self.permute_storage_transactions(transactions_dict, i, buy_index, energy_capacity_delta_buy, resource_capacity_delta, buy_accept_type, 
                                                                  sell_index, energy_capacity_delta_sell, t)
                                    # Actualizar los valores del elemento en la lista de mérito
                                    ba_res[k] -= resource_capacity_delta_traded
                                    if buy_accept_type == 'buy':
                                        ba_energy[k] -= resource_capacity_delta_traded / self._efficiency_rps 
                                    else:
                                        ba_energy[k] -= 0
                                    
                                    
                                    # Si el recurso disponible se ha agotado, eliminar la fila
                                    if ba_res[k] <= self.EPS:
                                        ba_active[k] = False
                                    
                                    sell_res[j] += resource_capacity_delta_traded
                                    sell_energy[j] += resource_capacity_delta_traded * self._efficiency_rcs
                                    if sell_res[j] >= -self.EPS:
                                        sell_active[j] = False
    
                                    transaction_bool = True
                                    offset = buy_index-start
                                    self._rss_current[offset:] +=resource_capacity_delta_traded
                                    self._rss_current[sell_index-start:] -= resource_capacity_delta_traded
                                    self._rss_global_max = self._rss_current.max()
 
                    # elif sell_price[j] >= self._rcs_only_total_variable_opex and self._rcs_only_operation_enabled is True:
                    #     sell_index = sell_idx[j]
                    #     resource_capacity_delta = 0
                    #     energy_capacity_delta_sell = min(self._estimated_generation_capacity, -sell_energy[j])

                    #     transactions_dict, i = self._calculate_transaction(transactions_dict, i,
                    #                                                        sell_index, -energy_capacity_delta_sell,
                    #                                                        -resource_capacity_delta,
                    #                                                        'rcs_only')
                    #     sell_res[j] += resource_capacity_delta
                    #     sell_energy[j] += energy_capacity_delta_sell
                    #     sell_active[j] = False
                            
                            
                    #     transaction_bool = True
                    elif sell_price[j] < ba_cost[k]:
                        break
                    j += 1
                    while j < length_sell and not sell_active[j]:
                        j+=1
                k += 1
                while k < length_ba and not ba_active[k]:
                    k+=1
        # Bypass:
        if self._bypass_operation_enabled:
            # for k in range(length_ba):
            #     if ba_cost[k] >= self._bypass_threshold_ba_cost:
            #         ba_active[k] = True
        
            # j = 0
            while j < length_sell and not sell_active[j]:
                j+=1
            while j < length_sell:
                k = ba_idx.tolist().index(sell_idx[j])
                if sell_price[j] > ba_cost_bypass[k] and ba_active[k]:
                    buy_index = ba_idx[k]
                    sell_index = sell_idx[j]
                    resource_capacity_delta = min(merit_buy_accept_df['resource_capacity_residual'][k], -merit_sell_df['resource_capacity_residual'][j])
                    
                    buy_accept_type =  'buy' if ba_is_buy[k] else 'accept'
                    
                    if buy_accept_type == 'buy':
                        energy_capacity_delta_buy = resource_capacity_delta / self._efficiency_rps_bypass
                    else:
                        energy_capacity_delta_buy = 0
                    energy_capacity_delta_sell = resource_capacity_delta * self._efficiency_rcs_bypass
                    # Check if storage capacity is exceeded after transaction
        
    
                    transactions_dict, i = self._calculate_transaction(transactions_dict, i,
                                                                        buy_index, energy_capacity_delta_buy,
                                                                        resource_capacity_delta,
                                                                        'bypass')
    
                    transactions_dict, i = self._calculate_transaction(transactions_dict, i,
                                                                        sell_index, -energy_capacity_delta_sell,
                                                                        -resource_capacity_delta,
                                                                        'bypass')
    
                    # Actualizar los valores del elemento en la lista de mérito
                    ba_res[k] -= resource_capacity_delta
                    ba_energy[k] -= energy_capacity_delta_buy
                    
                    # Si el recurso disponible se ha agotado, eliminar la fila
                    ba_active[k] = False
                    
                    sell_res[j] += resource_capacity_delta
                    sell_energy[j] += energy_capacity_delta_sell
                    sell_active[j] = False
                j+=1
            
            
        # RCS Only:
        j = 0
        while j < length_sell and not sell_active[j]:
            j+=1
        while j < length_sell:
            if self._rcs_only_operation_enabled is True and sell_active[j] and sell_price[j] >= self._rcs_only_total_variable_opex:
                sell_index = sell_idx[j]
                resource_capacity_delta = 0
                energy_capacity_delta_sell = min(self._estimated_generation_capacity, -sell_energy[j])
    
                transactions_dict, i = self._calculate_transaction(transactions_dict, i,
                                                                   sell_index, -energy_capacity_delta_sell,
                                                                   -resource_capacity_delta,
                                                                   'rcs_only')
                sell_res[j] += resource_capacity_delta
                sell_energy[j] += energy_capacity_delta_sell
                sell_active[j] = False
                    
                    
                transaction_bool = True
            j+=1
        
        
        self.transactions_dict = transactions_dict
        df = pd.DataFrame.from_dict(transactions_dict, orient='index')
        
        df['energy_purchased']        = df['energy'].clip(lower=0)
        df['energy_sold'] = df['energy'].clip(upper=0)
        df['resource_delta_produced']             = df['resource_delta'].clip(lower=0)
        df['resource_delta_consumed'] = df['resource_delta'].clip(upper=0)
        
        transaction_df_raw = (
            df.groupby('index')[['energy_purchased','resource_delta_produced',
                                  'energy_sold','resource_delta_consumed']].sum()
        )
        
        # 2) Acciones por signo de energy (concatenadas)
        charging_actions = (
            df.loc[df['energy'] >= 0]
              .groupby('index')['action']
              .agg(lambda s: ','.join(s.astype(str)))
              .rename('action_charging')
        )
        
        discharging_actions = (
            df.loc[df['energy'] < 0]
              .groupby('index')['action']
              .agg(lambda s: ','.join(s.astype(str)))
              .rename('action_discharging')
        )
        
        # 3) Unir sin pisar lo numérico
        transaction_df_raw = (
            transaction_df_raw
              .join(charging_actions, how='left')
              .join(discharging_actions, how='left')
        )

        #transaction_df_raw = pd.DataFrame.from_dict(transactions_dict, orient='index').set_index('index').groupby('index').sum()
        consolidated_resource_inlet_flow, consolidated_resource_inlet_power_consumption = self._calculate_accept_transaction(transactions_dict)
        return transaction_df_raw, consolidated_resource_inlet_flow, consolidated_resource_inlet_power_consumption


                    
    def _calculate_transaction(self, transactions_dict, transaction_index, day_index, energy_capacity_delta, resource_capacity_delta, action):

        transaction_index += 1
        transactions_dict[transaction_index] = {
            'index': day_index,
            'energy': energy_capacity_delta,
            'resource_delta': resource_capacity_delta,
            'action': action,
        }

        return transactions_dict, transaction_index
    
    def _calculate_accept_transaction(self, transactions_dict):
        """
        Versión rápida sin DataFrames ni groupby:
        - Agrega 'resource_delta' por índice con numpy.add.at (maneja duplicados).
        - Para 'power_consumption_list' marca 1 en horas con 'accept' y toma el valor
          de self._resource_input_power_consumption_df en esas horas (sin multiplicar por el recurso).
        """
        # Longitud del horizonte [0..max_index]
        L = (self._day_count + sample_period_days) * 24
    
        # ---- 1) Recolecta las ACCEPT y agrégalas por índice ----
        acc_idx = []
        acc_res = []
        for tx in transactions_dict.values():
            if tx['action'] == 'accept':
                idx = int(tx['index'])
                if 0 <= idx < L:
                    acc_idx.append(idx)
                    acc_res.append(float(tx['resource_delta']))
    
        resource_delta_arr = np.zeros(L, dtype=float)
        if acc_idx:
            idxs = np.fromiter(acc_idx, dtype=np.int64)
            vals = np.fromiter(acc_res, dtype=np.float64)
            # Suma por índice (soporta índices repetidos)
            np.add.at(resource_delta_arr, idxs, vals)
    
        # ---- 2) Potencia de inlet "tal cual" en horas con accept (misma semántica que tu versión) ----
        power_arr = np.zeros(L, dtype=float)
        if acc_idx:
            unique_idxs = np.unique(idxs)  # horas con algún 'accept'
            # Tomamos la potencia de inlet en esas horas (si falta, 0.0)
            pc_series = self._resource_input_power_consumption_df.reindex(unique_idxs)
            power_arr[unique_idxs] = np.nan_to_num(pc_series.to_numpy(), nan=0.0)
    
        return resource_delta_arr.tolist(), power_arr.tolist()

    
    def find_permutation_candidate(self, transactions_dict, buy_index, sell_index):
        """
        Devuelve (t, using_storage) donde t es el ÍNDICE DE POSICIÓN en
        list(transactions_dict.keys()), igual que tu versión original.
        """
        keys = list(transactions_dict.keys())
        n = len(keys)
        td = transactions_dict  # binding local
        bi = int(buy_index)
        si = int(sell_index)
    
        using_storage = False
        t = 1  # igual que tu código: empieza en el segundo elemento
    
        # Igual que tu while original: garantiza que hay "siguiente" para comprobar pares
        while t < n - 1:
            cur = td[keys[t]]
            act = cur['action']
    
            # Salta tombstones rápidos (si los usas)
            if act == 'void':
                t += 1
                continue
    
            # Caso par (buy/accept) -> (sell)
            if act == 'buy' or act == 'accept':
                nxt = td[keys[t + 1]]
                if nxt['action'] == 'sell':
                    # Condición temporal exacta a la tuya
                    if nxt['index'] >= bi and cur['index'] <= si:
                        return t, False
                    else:
                        t += 2  # saltas directamente al siguiente par potencial
                        continue
    
                # No hay par "buy/accept -> sell": avanza uno
                t += 1
                continue
    
            # Caso venta desde storage
            if act == 'sell' and cur['index'] >= bi:
                using_storage = True
                return t, using_storage
    
            # Siguiente posición
            t += 1
    
        return None, False

    #TODO: modificar lógica de permutaciones en caso de que key_buy y sell_index o buy_index/key_sell ¿Puede que solo una pareja? sean iguales
    def permute_transactions(self, transactions_dict, i, buy_index, energy_capacity_delta_buy, resource_capacity_delta, buy_accept_type, 
                             sell_index, energy_capacity_delta_sell, t):
        """
        Optimized permute without dict reindexing and without aliasing bugs.
        Keeps inputs/outputs identical to original method.
        """
        transaction_keys = list(transactions_dict.keys())
        key_buy  = transaction_keys[t]
        key_sell = transaction_keys[t + 1]
    
        # ---- LEE Y GUARDA TODO LO NECESARIO ANTES DE MUTAR ----
        ob = transactions_dict[key_buy]
        os = transactions_dict[key_sell]
    
        original_resource_delta = float(ob['resource_delta'])   # > 0
        ob_idx    = int(ob['index'])
        ob_energy = float(ob['energy'])
        ob_action = ob['action']                                # 'buy' o 'accept'
    
        os_idx    = int(os['index'])
        os_energy = float(os['energy'])
        # -------------------------------------------------------
    
        # Ajusta si la nueva operación pide más recurso del disponible en el par original
        if original_resource_delta < resource_capacity_delta:
            f = original_resource_delta / resource_capacity_delta
            energy_capacity_delta_buy  *= f
            energy_capacity_delta_sell *= f
            resource_capacity_delta     = original_resource_delta
    
        # Tombstone del par original (sin borrar ni reindexar)
        ob['energy'] = 0.0
        ob['resource_delta'] = 0.0
        ob['action'] = 'void'
    
        os['energy'] = 0.0
        os['resource_delta'] = 0.0
        os['action'] = 'void'
    
        # Helper para appends (evita overhead de _calculate_transaction)
        def _append_tx(idx, energy, res, action):
            nonlocal i, transactions_dict
            i += 1
            transactions_dict[i] = {
                'index': int(idx),
                'energy': float(energy),
                'resource_delta': float(res),
                'action': action
            }
            return i
    
        # 1) Nueva compra/aceptación para el evento a introducir
        _append_tx(buy_index,  energy_capacity_delta_buy,  resource_capacity_delta,      buy_accept_type)
    
        # 2) Venta correspondiente del par original
        _append_tx(os_idx,    -energy_capacity_delta_sell, -resource_capacity_delta,     'sell')
    
        # 3) Compra original (si fue 'accept', su energía es 0)
        ecb0 = 0.0 if ob_action == "accept" else energy_capacity_delta_buy
        _append_tx(ob_idx,     ecb0,                        resource_capacity_delta,      ob_action)
    
        # 4) Nueva venta del evento a introducir
        _append_tx(sell_index,-energy_capacity_delta_sell, -resource_capacity_delta,      'sell')
    
        # 5) Resto del par original (si queda capacidad)
        remaining_capacity = original_resource_delta - resource_capacity_delta
        if remaining_capacity > self.EPS:
            scale = remaining_capacity / original_resource_delta
            _append_tx(ob_idx,  ob_energy  * scale,  remaining_capacity,  ob_action)
            _append_tx(os_idx,  os_energy  * scale, -remaining_capacity,  'sell')
    
        return transactions_dict, i, resource_capacity_delta


    def permute_storage_transactions(self, transactions_dict, i, buy_index, energy_capacity_delta_buy, resource_capacity_delta, buy_accept_type,
                                     sell_index, energy_capacity_delta_sell, t):
        """
        Optimized version:
          - No dict deletions or O(n) reindex; tombstone original storage-sell.
          - Append-only for new transactions.
          - Returns transactions_dict REORDERED so that storage-originated sells created here
            appear at the top of the dictionary starting from key=1 (we preserve key=1 if not void).
        Inputs/outputs identical to original method signature.
        """
        transaction_keys = list(transactions_dict.keys())
        key_sell = transaction_keys[t]
        os = transactions_dict[key_sell]
    
        # -------- read everything needed BEFORE mutating (avoid aliasing) --------
        os_idx    = int(os['index'])
        os_energy = float(os['energy'])
        # storage sell => resource_delta is negative; capacity available (positive):
        original_resource_delta = float(-os['resource_delta'])
        # ------------------------------------------------------------------------
    
        # (1) Scale down if requested Δ exceeds available storage in the original sell
        if original_resource_delta < resource_capacity_delta:
            f = original_resource_delta / resource_capacity_delta
            energy_capacity_delta_buy  *= f
            energy_capacity_delta_sell *= f
            resource_capacity_delta     = original_resource_delta
    
        # (2) Tombstone original storage sell (no delete, no reindex)
        os['energy'] = 0.0
        os['resource_delta'] = 0.0
        os['action'] = 'void'
    
        # Helper: append-only (avoid overhead of _calculate_transaction)
        def _append_tx(idx, energy, res, action):
            nonlocal i, transactions_dict
            i += 1
            transactions_dict[i] = {
                'index': int(idx),
                'energy': float(energy),
                'resource_delta': float(res),
                'action': action
            }
            return i  # return new key for possible prioritization
    
        # --- Create the new set of transactions (append-only) ---
        # A) New storage-originated SELL at sell_index (this must go to the top zone)
        key_new_sell = _append_tx(sell_index, -energy_capacity_delta_sell, -resource_capacity_delta, 'sell')
    
        # B) New BUY/ACCEPT corresponding to the event being introduced
        _append_tx(buy_index, energy_capacity_delta_buy, resource_capacity_delta, buy_accept_type)
    
        # C) Auxiliary SELL at the original sell index (to close the Δ path)
        key_aux_sell = _append_tx(os_idx, -energy_capacity_delta_sell, -resource_capacity_delta, 'sell')
    
        # D) Remaining capacity from original storage sell (if any) — this is also storage-based SELL
        storage_sell_keys = [key_new_sell]  # will be prioritized
        remaining_capacity = original_resource_delta - resource_capacity_delta
        if remaining_capacity > self.EPS:
            scale = remaining_capacity / original_resource_delta
            key_remaining = _append_tx(os_idx, os_energy * scale, -remaining_capacity, 'sell')
            storage_sell_keys.append(key_remaining)
    
        # --- REORDER the dictionary so that these storage sells appear at the top from key=1 ---
        # Build ordered list of (key, value) preserving original insertion order where needed.
        items = list(transactions_dict.items())
    
        # Filter out tombstones if you don't want them in the final dict;
        # if you prefer to keep them (they sum to 0 anyway), comment the next line.
        items = [(k, v) for (k, v) in items if v.get('action') != 'void']
    
        # 1) Keep original key=1 first if it exists and is not tombstone
        head = []
        if 1 in transactions_dict and transactions_dict[1].get('action') != 'void':
            # Find the (1, value) pair in items
            for idx, (k, v) in enumerate(items):
                if k == 1:
                    head.append(items.pop(idx))  # remove from items and keep as head
                    break
    
        # 2) Put storage sells we just created right after head (preserving their creation order)
        storage_set = set(storage_sell_keys)
        stor = [(k, v) for (k, v) in items if k in storage_set]
        rest = [(k, v) for (k, v) in items if k not in storage_set]
    
        ordered = head + stor + rest
    
        # Rebuild dict with keys starting from 1
        transactions_dict = {new_k: v for new_k, (_, v) in enumerate(ordered, start=1)}
    
        return transactions_dict, i, resource_capacity_delta


    def calculate_trading_performance(self):
        """
        Calculates the performance indicator of the trading algorithm.
        
        Parameters:
            consolidated_operation_df (pd.DataFrame): DataFrame containing trading operations.
    
        Returns:
            float: Performance indicator value.
        """
        # First term: Sum of (Energy < 0) * Spot_Price2
        consolidated_operation_df = self._consolidated_operation_df
        negative_energy_cost = (consolidated_operation_df['energy_sold'] < 0) * \
                               (consolidated_operation_df['energy_sold'] * consolidated_operation_df['Spot_Price2'])
    
        # Second term: Sum of (Energy >= 0) * marginal_cost_buy
        positive_energy_cost = (consolidated_operation_df['energy_purchased'] >= 0) * \
                               (consolidated_operation_df['energy_purchased'] * consolidated_operation_df['marginal_cost_buy'])
    
        # Handle _consolidated_resource_inlet_flow structure
        if isinstance(self._consolidated_resource_inlet_flow, list):
            resource_inlet_value = sum(self._consolidated_resource_inlet_flow)  # Sum values if it's a list
        elif isinstance(self._consolidated_resource_inlet_flow, dict):
            resource_inlet_value = self._consolidated_resource_inlet_flow.get('value', 0)  # Extract value if it's a dict
        elif hasattr(self._consolidated_resource_inlet_flow, 'sum'):  # If it's a pandas Series or DataFrame column
            resource_inlet_value = self._consolidated_resource_inlet_flow.sum()
        else:
            resource_inlet_value = 0  # Default to 0 if unexpected format
    
        # Compute total resource inlet cost
        resource_inlet_cost = resource_inlet_value * self._resource_inlet_cost
    
        # Calculate performance indicator
        performance = -negative_energy_cost.sum() - positive_energy_cost.sum() + resource_inlet_cost
    
        return performance

