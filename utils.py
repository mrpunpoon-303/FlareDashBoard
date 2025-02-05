import pandas as pd
import base64
import io

def create_frequency_table(data, period=None, start_period=None, end_period=None, max_upper=10):
    """Process data to create frequency table"""
    if period:
        data_filtered = data[data["Start_Date_time"].dt.to_period("M").astype(str) == period]
    elif start_period and end_period:
        periods = data["Start_Date_time"].dt.to_period("M").astype(str)
        data_filtered = data[(periods >= start_period) & (periods <= end_period)]
    else:
        return None

    # Exclude "Self Practice"
    data_filtered = data_filtered[~data_filtered["Class_Name"].str.contains("Self Practice", case=False, na=False)]

    # Calculate booking frequencies
    booking_frequencies = data_filtered.groupby("Id_Person").size()

    # Create frequency table
    table = pd.DataFrame({
        "Freq": list(range(1, max_upper + 1)) + [f">{max_upper}"],
        "#Students": [sum(booking_frequencies == i) for i in range(1, max_upper + 1)] + 
                    [sum(booking_frequencies > max_upper)],
        "Cum 1->": [sum(booking_frequencies <= i) for i in range(1, max_upper + 1)] + 
                  [len(booking_frequencies)],
        "Cum ->End": [len(booking_frequencies) - sum(booking_frequencies <= i) for i in range(1, max_upper + 1)] + 
                    [sum(booking_frequencies > max_upper)]
    })

    # Add student details
    def get_student_details(freq):
        if isinstance(freq, str) and freq.startswith(">"):
            ids = booking_frequencies[booking_frequencies > max_upper].index
        else:
            ids = booking_frequencies[booking_frequencies == freq].index
        
        names = data_filtered[data_filtered["Id_Person"].isin(ids)]["FirstName"].drop_duplicates()
        return ", ".join([f"{name} : {id}" for name, id in zip(names, ids)])

    table["Details"] = [get_student_details(freq) for freq in table["Freq"]]
    return table

def parse_contents(contents):
    """Parse uploaded file contents"""
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        df = pd.read_excel(io.BytesIO(decoded))
        df["Start_Date_time"] = pd.to_datetime(df["Start_Date_time"], errors="coerce")
        return df, None
    except Exception as e:
        return None, str(e)

def get_monthly_selector(periods):
    from dash import dcc
    return dcc.Dropdown(
        id={'type': 'period', 'mode': 'monthly'},
        options=[{'label': p, 'value': p} for p in periods],
        value=periods[-1],
        className="w-full"
    )

def get_range_selector(periods):
    from dash import html, dcc
    return html.Div([
        html.Label("Start Period:", className="font-medium"),
        dcc.Dropdown(
            id={'type': 'period', 'mode': 'start'},
            options=[{'label': p, 'value': p} for p in periods],
            value=periods[0],
            className="w-full mb-2"
        ),
        html.Label("End Period:", className="font-medium"),
        dcc.Dropdown(
            id={'type': 'period', 'mode': 'end'},
            options=[{'label': p, 'value': p} for p in periods],
            value=periods[-1],
            className="w-full"
        )
    ])