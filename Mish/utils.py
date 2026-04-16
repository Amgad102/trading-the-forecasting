import sys
import time


def calculate_rss_series(resource_consumption_series, rss_start):
    index_start = resource_consumption_series.index[0]
    resource_consumption_series.update({index_start: resource_consumption_series.loc[index_start].copy() + rss_start})
    rss_df = resource_consumption_series.cumsum()
    return rss_df.rename('rss')


def progressbar(it, prefix="", size=60, out=sys.stdout):
    count = len(it)
    start = time.time()

    def show(j):
        x = int(size * j / count)
        remaining = ((time.time() - start) / j) * (count - j)

        # mins, sec = divmod(remaining, 60)
        # time_str = f"{int(mins):02}:{sec:05.2f}"

        print(f"{prefix}[{u'█' * x}{('.' * (size - x))}] {j}/{count}", end='\r', file=out,
              flush=True)

    for i, item in enumerate(it):
        yield item
        show(i + 1)
    print("", flush=True, file=out, end='\r')

import inspect

def get_rate(rate_input, **kwargs):
    """
    Evalúa una tasa que puede ser un número constante o una función.
    Si es función, se le pasan solo los argumentos que realmente acepta.
    """
    if callable(rate_input):
        # Obtener los parámetros que la función acepta
        sig = inspect.signature(rate_input)
        accepted_params = sig.parameters.keys()

        # Filtrar kwargs según lo que la función acepta
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in accepted_params}

        try:
            return rate_input(**filtered_kwargs)
        except Exception as e:
            raise RuntimeError(f"Error al evaluar función rate: {e}")
    else:
        return rate_input

def get_resource_inlet_power_consumption_rate(rate_input, resource_inlet):
    if callable(rate_input):
        return rate_input(resource_inlet)
    else:
        return rate_input
