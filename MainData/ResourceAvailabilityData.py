import pandas as pd
import os
import matplotlib.pyplot as plt
from inputs import resource_inlet_power_consumption_rate
from Mish.utils import get_resource_inlet_power_consumption_rate

class ResourceAvailabilityData:
    def __init__(self, filename, project_year_start, project_life):
        input_filepath = os.path.join("MainData", filename)
        try:
            resource_data_df = pd.read_csv(input_filepath, sep=',')
            # O comprobar que el número de columnas es razonable:
            if resource_data_df.shape[1] <= 1:
                raise ValueError("Likely wrong separator, trying fallback.")
        except Exception:
            resource_data_df = pd.read_csv(input_filepath, sep=';')
        
        # Convertir a DateTime y establecer como índice
        resource_data_df['DateTime'] = pd.to_datetime(resource_data_df[['Year', 'Month', 'Day', 'Hour']])
        resource_data_df = self._calculate_resource_inlet_power_consumption_df(resource_data_df, resource_inlet_power_consumption_rate)
        
        #resource_data_df.set_index('DateTime', inplace=True)
        
        # Agrupar por hora y calcular el promedio
        #resource_data_df = resource_data_df.resample('H').mean().reset_index()
        
        # Extraer la hora y el día del año
        resource_data_df['day_of_year'] = resource_data_df['DateTime'].dt.dayofyear
        resource_data_df['Hour'] = resource_data_df['DateTime'].dt.hour
        
        # Agrupar por 'day_of_year' y 'Hour' y calcular la media
        resource_data_df = resource_data_df.groupby(['day_of_year', 'Hour'], as_index=False).mean()
                
        # Preparar DataFrame extendido
        self._project_life = project_life
        self._project_year_start = project_year_start
        resource_data_df_extended = self._extend_resource_data_df(resource_data_df, project_year_start, project_life)
        
        # Eliminar columnas innecesarias
        resource_data_df.drop(columns=['day_of_year'], errors='ignore', inplace=True)
        
        self.resource_data_df = resource_data_df_extended
        
    def _calculate_resource_inlet_power_consumption_df(self, df, resource_inlet_power_consumption_rate):
        """
        Adds a 'Power_Consumption' column to the DataFrame based on the resource inlet flow and a given rate.
        If the column already exists, returns the DataFrame unchanged.
        """
    
        # 1. If the column already exists, return the original DataFrame
        if 'Power_Consumption' in df.columns:
            return df
    
        # 2. Compute element-wise power consumption
        def compute_power(resource_inlet_value):
            rate = get_resource_inlet_power_consumption_rate(
                resource_inlet_power_consumption_rate,
                resource_inlet_value
            )
            return resource_inlet_value * rate
    
        df['Power_Consumption'] = df['Resource_Available'].apply(compute_power)
    
        return df


    
    def _extend_resource_data_df(self, df, start_year, project_life):
        """ Extiende los datos a lo largo de la vida del proyecto """
        df_list = []
        for year in range(start_year, start_year + project_life):
            temp_df = df.copy()
            temp_df['Year'] = year
            df_list.append(temp_df)
        
        return pd.concat(df_list, ignore_index=True)
    
    def get_resource_data_df(self):
        """ Devuelve el DataFrame con los datos extendidos """
        return self.resource_data_df
    
    def plot_resource_distribution(self):
        """ Genera una gráfica de la distribución de recurso disponible """
        plt.figure(figsize=(12, 6))
        font_size = 14

        # Asegurar que los datos están ordenados
        resource_data_df_sorted = self.resource_data_df.sort_values(by=["Year", "Month", "Day", "Hour"])

        # Graficar la distribución de la energía térmica
        plt.plot(resource_data_df_sorted["DateTime"], 
                 resource_data_df_sorted["Resource_Available"], 
                 label="Energía Térmica Disponible", color='orange')

        # Etiquetas y formato
        plt.xlabel("Fecha", fontsize=font_size)
        plt.ylabel("Recurso", fontsize=font_size)
        plt.title("Distribución de Recurso a lo Largo del Tiempo", fontsize=font_size+2)
        plt.legend()
        plt.grid()
        plt.xticks(rotation=45)
        
        plt.show()
