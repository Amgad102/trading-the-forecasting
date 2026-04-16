import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from inputs import electricity_price_file, YEAR_START, negative_prices_correction, positive_prices_correction, forbidden_tariff_periods, generation_restrictions_file, is_cost_driven
from inputs import electricity_tax, margin_tradingcompany_energy
from .TariffPeriod import TariffPeriod

class ElectricityPriceData:
    def __init__(self, project_life, price_mean_modifier=1, price_std_modifier=1, price_minimum=0, PPA=None, subsidy_per_mwh=0, PPA_sales=None):
        self._write_message(price_mean_modifier, price_std_modifier, price_minimum, PPA, subsidy_per_mwh, PPA_sales)
        if electricity_price_file is None:
            self._input_filepath = os.path.join("MainData", f"ElectricityPriceData{YEAR_START}.csv")
        else:
            self._input_filepath = os.path.join("MainData", electricity_price_file)
            
        self._electricity_price_df = pd.read_csv(self._input_filepath)
        self._electricity_price_df['Hour'] -= 1
        self._electricity_price_df['Hour'] = self._electricity_price_df['Hour'] % 24
        self._electricity_price_df['DateTime'] = pd.to_datetime(self._electricity_price_df[['Year', 'Month', 'Day', 'Hour']])
        self._electricity_price_df["Spot_Price1"] = self._electricity_price_df["Spot_Price2"]  # igualar ambas columnas al precio de cierre
        self._electricity_price_df_original = self._electricity_price_df.copy()  # Guarda una copia del original antes de ajustar
        self.alpha = price_mean_modifier
        self.beta = price_std_modifier
        self._electricity_price_df = self._adjust_prices(price_minimum)
        self.agregar_periodo_facturacion()
        self._electricity_price_df.loc[self._electricity_price_df['TariffPeriod'].isin(forbidden_tariff_periods), 'Spot_Price1'] = 9999
        
        
        # if PPA is not None:
        #     #self._electricity_price_df["Spot_Price1"] = self._electricity_price_df["Spot_Price1"].clip(upper=PPA)
        #     #self._electricity_price_df["Spot_Price1"] = (PPA + self._electricity_price_df["EnergyTermTolls"]*1000+self._electricity_price_df["EnergyTermOtherCharges"]*1000+margin_tradingcompany_energy*1000)*(1+electricity_tax/100)
        #     self._electricity_price_df["Spot_Price1"] = PPA
        # else:

        self._electricity_price_df["Spot_Price1"] = (self._electricity_price_df["Spot_Price1"] + self._electricity_price_df["EnergyTermTolls"]*1000+self._electricity_price_df["EnergyTermOtherCharges"]*1000+margin_tradingcompany_energy*1000)*(1+electricity_tax/100)
        if is_cost_driven == True:
            self._electricity_price_df["Spot_Price2"] = self._electricity_price_df["Spot_Price1"]
        if PPA_sales is not None:
            self._electricity_price_df["Spot_Price2"] = PPA_sales
        if subsidy_per_mwh > 0:
            self._electricity_price_df["Spot_Price2"] = self._electricity_price_df["Spot_Price2"] + subsidy_per_mwh
                
        ## Extend dataframe to project_life
        self._electricity_price_df = self._extend_df(project_life, self._electricity_price_df)     
        
        if generation_restrictions_file is not None:
            self._generation_restrictions_filepath = os.path.join("MainData", generation_restrictions_file)
            self._generation_restrictions_df = pd.read_csv(self._generation_restrictions_filepath)
            self._generation_restrictions_df['Hour'] -= 1
            self._generation_restrictions_df['Hour'] = self._generation_restrictions_df['Hour'] % 24
            self._generation_restrictions_df['DateTime'] = pd.to_datetime(self._generation_restrictions_df[['Year', 'Month', 'Day', 'Hour']])
            self._generation_restrictions_df = self._extend_df(project_life, self._generation_restrictions_df)             
            # Modificar Spot_Price2 donde "Generation" es True en el DataFrame de restricciones
            self._electricity_price_df.loc[self._generation_restrictions_df["Generation"], "Spot_Price2"] = -9999

    def _write_message(self, price_mean_modifier=1, price_std_modifier=1, price_minimum=0, PPA=None, subsidy_per_mwh=0, PPA_sales=None):
        if electricity_price_file is None:
            message = f"Spot price distribution for the year {YEAR_START} loaded as reference. "
        else:
            message = f"Spot price distribution in file {electricity_price_file} loaded as reference"
        # Check if the price distribution is modified
        if price_mean_modifier == 1 and price_std_modifier == 1:
            message += "The distribution is NOT modified. "
        else:
            message += (
                f"The distribution has been modified according to the mean modifier ({price_mean_modifier}) "
                f"and standard deviation modifier ({price_std_modifier}). "
            )
        
            # Check for negative prices correction
            if negative_prices_correction is None:
                message += f"No correction has been applied for prices below the minimum price of {price_minimum} €/MWh. "
            elif negative_prices_correction == 'filtering':
                message += f"All values below the minimum price of {price_minimum} €/MWh have been set to {price_minimum}. "
            elif negative_prices_correction == 'smoothing':
                message += (
                    f"Values below the minimum price of {price_minimum} €/MWh have been corrected using an exponential distribution "
                    f"to reduce (smooth) the occurrence of prices below {price_minimum}. "
                )
        
            # Check for positive prices correction
            if positive_prices_correction:
                message += "Prices above the minimum price have been adjusted. "
            else:
                message += "Prices above the minimum price have NOT been adjusted. "
        
        # Check for PPA usage
        if PPA is not None:
            message += f"A photovoltaic PPA with a value of {PPA} €/MWh has been used for purchase prices. "
        
        # Check for PPA sales usage
        if PPA_sales is not None:
            message += f"A PPA for sales with a value of {PPA_sales} €/MWh has been selected for sales prices. "
        
        # Check for subsidy per MWh
        if subsidy_per_mwh > 0:
            message += f"Purchase prices have been rescaled by adding a subsidy of {subsidy_per_mwh} €/MWh. "
        
        print(message)


    def update_spot_price1_PPA_from_weather_df(self, PPA, weather_data_df):
        self._electricity_price_df["Spot_Price1"] = np.where(weather_data_df["GHI"] > 0, PPA, 9999)
        return self._electricity_price_df
    
    def get_electricity_price_df(self):
        return self._electricity_price_df

    def _extend_df(self, project_life, original_dataframe):
        """
        Extiende el DataFrame de precios de electricidad hasta cubrir la vida del proyecto.
        Si el DataFrame ya cubre toda la vida del proyecto, no hace nada.
        Si faltan años, repite el último año hasta completar la duración requerida.
        """
        # Obtener el rango de años en los datos actuales
        min_year = original_dataframe["Year"].min()
        max_year = original_dataframe["Year"].max()
        
        # Calcular el año final esperado
        expected_final_year = min_year + project_life - 1  # Año inicial + vida del proyecto - 1
        
        # Si ya cubre la vida del proyecto, no hacer nada
        if max_year >= expected_final_year:
            return original_dataframe
    
        # Si faltan años, repetir el último año hasta completar la vida del proyecto
        temp_df = original_dataframe.copy()
        last_year_df = temp_df[temp_df["Year"] == max_year]  # Filtrar solo el último año disponible
    
        for year in range(max_year + 1, expected_final_year + 1):
            extended_year = last_year_df.copy()
            extended_year.loc[:, "Year"] = int(year)  # Actualizar el año
            original_dataframe = pd.concat([original_dataframe, extended_year], ignore_index=True)
        original_dataframe = original_dataframe.reset_index(drop=True)
        return original_dataframe

    # def _extend_electricity_price_df_old(self, project_life):
    #     temp_df = self._electricity_price_df.copy()
    #     for _ in range(1, project_life):
    #         temp_df.loc[:, 'Year'] += 1
    #         self._electricity_price_df = pd.concat([self._electricity_price_df, temp_df])
    #     return self._electricity_price_df

    def _adjust_prices(self, price_minimum):
        mu_X = self._electricity_price_df['Spot_Price1'].mean()
        sigma_X = self._electricity_price_df['Spot_Price1'].std()
        CV_X = sigma_X/mu_X
        threshold = 5
        no_zeros_X = self._electricity_price_df.query('Spot_Price1 < @threshold').shape[0]
        
        a = self.beta*self.alpha ## mean coefficient
        b = (self.alpha - self.alpha*self.beta) * mu_X ## CV coefficient
        for column in ['Spot_Price1', 'Spot_Price2']:
            self._electricity_price_df[column] = self._electricity_price_df[column] * a + b
        electricity_price_mean_std_df = self._electricity_price_df.copy()
        mean_mod = electricity_price_mean_std_df['Spot_Price1'].mean()
        std_mod = electricity_price_mean_std_df['Spot_Price1'].std()
        CV_mod = std_mod/mean_mod
        no_zeros_mod = electricity_price_mean_std_df.query('Spot_Price1 < @threshold').shape[0]
        
        lambda_param = 10 # Decay parameter for exponential distribution
        def ajustar_valor_exponencial(valor, lambda_param, price_minimum):
            if valor >= price_minimum:
                return valor
            exp_value = np.random.exponential(scale=1 / lambda_param)
            # Scale value in range [valor, 0]
            return valor * (exp_value / (exp_value + 1))
        
        
        # Distribución precio suavizada en torno a precio mínimo:
        if negative_prices_correction == 'smoothing':
            electricity_price_df_smoothed = self._electricity_price_df.copy()
            electricity_price_df_smoothed["Spot_Price1"] = electricity_price_df_smoothed["Spot_Price1"].apply(lambda x: ajustar_valor_exponencial(x, lambda_param, price_minimum))
            electricity_price_df_smoothed["Spot_Price2"] = electricity_price_df_smoothed["Spot_Price1"]
            electricity_price_df_corrected = electricity_price_df_smoothed.copy()
        elif negative_prices_correction == 'filtering':           
            # Distribución precio filtrada a precio mínimo:
            electricity_price_df_filtered = self._electricity_price_df.copy()
            electricity_price_df_filtered["Spot_Price1"] = electricity_price_df_filtered["Spot_Price1"].clip(lower=price_minimum)
            electricity_price_df_filtered["Spot_Price2"] = electricity_price_df_filtered["Spot_Price1"]
            electricity_price_df_corrected = electricity_price_df_filtered.copy()
        else:
            electricity_price_df_corrected = self._electricity_price_df.copy()
            
        self._electricity_price_df = electricity_price_df_corrected.copy()
        mean_actual = self._electricity_price_df['Spot_Price1'].mean()
        std_actual = self._electricity_price_df['Spot_Price1'].std()
        CV_actual = std_actual/mean_actual
        no_zeros = self._electricity_price_df.query('Spot_Price1 < @threshold').shape[0]    

        if positive_prices_correction == True:
            # Calcular el crédito
            credito = np.abs(electricity_price_mean_std_df["Spot_Price1"] - electricity_price_df_corrected["Spot_Price1"])
            credito_total = np.sum(credito)
            horas_sobre_umbral = electricity_price_df_corrected['Spot_Price1'] > price_minimum
            numero_horas_sobre_umbral = np.sum(horas_sobre_umbral)
            if numero_horas_sobre_umbral > 0:
                credito_por_hora = credito_total / numero_horas_sobre_umbral
            else:
                credito_por_hora = 0
            electricity_price_df_fully_corrected = electricity_price_df_corrected.copy()
            electricity_price_df_fully_corrected.loc[horas_sobre_umbral, 'Spot_Price1'] += credito_por_hora
            electricity_price_df_fully_corrected['Spot_Price2'] = electricity_price_df_fully_corrected['Spot_Price1']
            self._electricity_price_df = electricity_price_df_fully_corrected
        
        
        return self._electricity_price_df

    def agregar_periodo_facturacion(self):
        periodo_facturacion = TariffPeriod(current_year=YEAR_START)
        self._electricity_price_df = periodo_facturacion.agregar_periodo_facturacion_a_dataframe(self._electricity_price_df, 'DateTime', 'Hour')
        return self._electricity_price_df

    def _calcular_peaje_potencia_especifica(self, df):
        # Cuenta los valores de cada tipo
        potencia_especifica = sum(df.termino_potencia_peajes["6.1 TD"])
        return potencia_especifica #EUR/kW/año
    
    def plot_prices(self):
        plt.figure(figsize=(10, 5))
        plt.scatter(self._electricity_price_df.index, self._electricity_price_df['Spot_Price1'], label='Adjusted Prices', s=1)
        plt.scatter(self._electricity_price_df_original.index, self._electricity_price_df_original['Spot_Price1'], label='Original Prices', s=1)
        plt.title('Comparison of Original and Adjusted Spot Price1')
        plt.xlabel('Date')
        plt.ylabel('Price (€/MWh)')
        plt.legend()
        plt.grid(True)
        plt.show()
        plt.figure(figsize=(10, 5))
        plt.scatter(self._electricity_price_df.index, self._electricity_price_df['Spot_Price2'], label='Adjusted Prices', s=1)
        plt.scatter(self._electricity_price_df_original.index, self._electricity_price_df_original['Spot_Price2'], label='Original Prices', s=1)
        plt.title('Comparison of Original and Adjusted Spot Price2')
        plt.xlabel('Date')
        plt.ylabel('Price (€/MWh)')
        plt.legend()
        plt.grid(True)
        plt.show()
