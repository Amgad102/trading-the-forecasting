import pandas as pd
import os
import matplotlib.pyplot as plt

class ThermalPowerData:
    def __init__(self, filename, project_year_start, project_life):
        input_filepath = os.path.join("MainData", filename)
        thermal_power_data_df = pd.read_csv(input_filepath)
        
        # Convertir a DateTime y establecer como índice
        thermal_power_data_df['DateTime'] = pd.to_datetime(thermal_power_data_df[['Year', 'Month', 'Day', 'Hour']])
        thermal_power_data_df.set_index('DateTime', inplace=True)
        
        # Agrupar por hora y calcular el promedio
        thermal_power_data_df = thermal_power_data_df.resample('H').mean().reset_index()
        
        # Extraer la hora y el día del año
        thermal_power_data_df['day_of_year'] = thermal_power_data_df['DateTime'].dt.dayofyear
        thermal_power_data_df['Hour'] = thermal_power_data_df['DateTime'].dt.hour
        
        # Agrupar por 'day_of_year' y 'Hour' y calcular la media
        thermal_power_data_df = thermal_power_data_df.groupby(['day_of_year', 'Hour'], as_index=False).mean()
                
        # Preparar DataFrame extendido
        self._project_life = project_life
        self._project_year_start = project_year_start
        thermal_power_data_df_extended = self._extend_thermal_power_data_df(thermal_power_data_df, project_year_start, project_life)
        
        # Eliminar columnas innecesarias
        thermal_power_data_df.drop(columns=['day_of_year'], errors='ignore', inplace=True)
        
        self.thermal_power_data_df = thermal_power_data_df_extended
        
    def _extend_thermal_power_data_df(self, df, start_year, project_life):
        """ Extiende los datos térmicos a lo largo de la vida del proyecto """
        df_list = []
        for year in range(start_year, start_year + project_life):
            temp_df = df.copy()
            temp_df['Year'] = year
            df_list.append(temp_df)
        
        return pd.concat(df_list, ignore_index=True)
    
    def get_thermal_power_data_df(self):
        """ Devuelve el DataFrame con los datos de energía térmica extendidos """
        return self.thermal_power_data_df
    
    def plot_thermal_power_distribution(self):
        """ Genera una gráfica de la distribución de la energía térmica disponible """
        plt.figure(figsize=(12, 6))
        font_size = 14

        # Asegurar que los datos están ordenados
        thermal_power_data_df_sorted = self.thermal_power_data_df.sort_values(by=["Year", "Month", "Day", "Hour"])

        # Graficar la distribución de la energía térmica
        plt.plot(thermal_power_data_df_sorted["DateTime"], 
                 thermal_power_data_df_sorted["Resource_Available"], 
                 label="Energía Térmica Disponible", color='orange')

        # Etiquetas y formato
        plt.xlabel("Fecha", fontsize=font_size)
        plt.ylabel("Energía Térmica Disponible (MWht)", fontsize=font_size)
        plt.title("Distribución de Energía Térmica a lo Largo del Tiempo", fontsize=font_size+2)
        plt.legend()
        plt.grid()
        plt.xticks(rotation=45)
        
        plt.show()
