def min_max_normalize(series):
    return (series - series.min()) / (series.max() - series.min())