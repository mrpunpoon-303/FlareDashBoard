from dash import html, dcc, Input, Output, State, callback
import pandas as pd
import plotly.graph_objs as go
from dash.exceptions import PreventUpdate
from io import StringIO
import dash

def create_monthly_user_booking_layout(show_upload=True):
    return html.Div([
        html.H1("Students Booking at Least N Times Per Month", className="text-2xl font-bold mb-4"),
        
        # Controls Container
        html.Div([
            # Period Selection
            html.Div([
                html.Div([
                    html.Label('Start Period:', className="block mb-2 font-medium"),
                    dcc.Dropdown(
                        id='start-period-dropdown',
                        className="w-full"
                    )
                ], className="w-1/2 pr-2"),
                
                html.Div([
                    html.Label('End Period:', className="block mb-2 font-medium"),
                    dcc.Dropdown(
                        id='end-period-dropdown',
                        className="w-full"
                    )
                ], className="w-1/2 pl-2")
            ], className="flex mb-4"),
            
            # Thresholds
            html.Div([
                html.Div([
                    html.Label('Threshold 1:', className="block mb-2 font-medium"),
                    dcc.Input(
                        id='threshold-1', 
                        type='number', 
                        value=3, 
                        min=0,
                        className="w-full p-2 border rounded"
                    )
                ], className="w-1/3 px-2"),
                
                html.Div([
                    html.Label('Threshold 2:', className="block mb-2 font-medium"),
                    dcc.Input(
                        id='threshold-2', 
                        type='number', 
                        value=4, 
                        min=0,
                        className="w-full p-2 border rounded"
                    )
                ], className="w-1/3 px-2"),
                
                html.Div([
                    html.Label('Threshold 3:', className="block mb-2 font-medium"),
                    dcc.Input(
                        id='threshold-3', 
                        type='number', 
                        value=5, 
                        min=0,
                        className="w-full p-2 border rounded"
                    )
                ], className="w-1/3 px-2")
            ], className="flex mb-4"),
            
            # Buttons Row
            html.Div([
                html.Button(
                    'Execute Analysis', 
                    id='execute-btn', 
                    n_clicks=0,
                    className="bg-green-500 text-white px-6 py-2 rounded hover:bg-green-600 mr-4"
                ),
                html.Button(
                    'Export Data (XLSX)', 
                    id='export-monthly-btn',
                    className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600"
                )
            ], className="mb-4")
        ], id='controls-section', style={'display': 'none'}),
        
        # Status message
        html.Div(id='status-message-monthly', className="mb-4"),
        
        # Results Section
        html.Div([
            dcc.Graph(id='monthly-users-graph')
        ], id='results-section-monthly', style={'display': 'none'}),
        
        # Store for chart data and download
        dcc.Store(id='chart-data-monthly'),
        dcc.Download(id="download-monthly-xlsx"),
        dcc.Loading(
            id="loading-monthly",
            type="default",
            children=html.Div(id="loading-output-monthly")
        )
    ], className="max-w-4xl mx-auto p-6")

def calculate_monthly_users(data, thresholds):
    """Calculate monthly user statistics based on booking thresholds"""
    data = data.copy()
    data.loc[:, "YearMonth"] = data["Start_Date_time"].dt.to_period("M")
    booking_frequencies = data.groupby(["YearMonth", "Id_Person"]).size().reset_index(name="Bookings")
    
    results = []
    for n in thresholds:
        counts = (
            booking_frequencies.groupby("YearMonth")["Bookings"]
            .apply(lambda x: (x >= n).sum())
            .reset_index(name=f"Users_>=_{n}")
        )
        counts["YearMonth"] = counts["YearMonth"].astype(str)
        results.append(counts)

    merged_results = results[0]
    for i in range(1, len(results)):
        merged_results = pd.merge(merged_results, results[i], on="YearMonth", how="outer")
    
    merged_results = merged_results.rename(columns={"YearMonth": "Month"})
    return merged_results

def register_monthly_user_booking_callbacks(app):
    @app.callback(
        [Output('start-period-dropdown', 'options'),
         Output('end-period-dropdown', 'options'),
         Output('start-period-dropdown', 'value'),
         Output('end-period-dropdown', 'value'),
         Output('controls-section', 'style')],
        Input('shared-stored-data', 'data')
    )
    def update_period_dropdowns(stored_data):
        if not stored_data:
            return [], [], None, None, {'display': 'none'}
            
        df = pd.read_json(StringIO(stored_data['data']), orient='split')
        periods = sorted(df["Start_Date_time"].dt.to_period("M").astype(str).unique())
        options = [{'label': p, 'value': p} for p in periods]
        
        return options, options, periods[0], periods[-1], {'display': 'block'}

    @app.callback(
        [Output('monthly-users-graph', 'figure'),
         Output('results-section-monthly', 'style'),
         Output('status-message-monthly', 'children'),
         Output('status-message-monthly', 'className'),
         Output('chart-data-monthly', 'data')],
        Input('execute-btn', 'n_clicks'),
        [State('shared-stored-data', 'data'),
         State('start-period-dropdown', 'value'),
         State('end-period-dropdown', 'value'),
         State('threshold-1', 'value'),
         State('threshold-2', 'value'),
         State('threshold-3', 'value')]
    )
    def update_graph(n_clicks, stored_data, start_period, end_period, 
                    threshold1, threshold2, threshold3):
        if not n_clicks or not stored_data:
            raise PreventUpdate
            
        try:
            df = pd.read_json(StringIO(stored_data['data']), orient='split')
            
            filtered_data = df[
                (df["Start_Date_time"].dt.to_period("M").astype(str) >= start_period) &
                (df["Start_Date_time"].dt.to_period("M").astype(str) <= end_period)
            ]
            
            if "Class_Name" in filtered_data.columns:
                filtered_data = filtered_data[~filtered_data["Class_Name"].str.contains("Self Practice", case=False, na=False)]
            
            thresholds = [t for t in [threshold1, threshold2, threshold3] if t > 0]
            if not thresholds:
                raise ValueError("Please set at least one threshold greater than 0")
            
            stats = calculate_monthly_users(filtered_data, thresholds)
            total_bookings = filtered_data.groupby(filtered_data["Start_Date_time"].dt.to_period("M")).size()
            total_bookings = total_bookings.reindex(stats["Month"], fill_value=0)
            
            export_data = stats.copy()
            export_data['Total_Bookings'] = total_bookings.values
            
            fig = go.Figure()
            
            for n in thresholds:
                column = f"Users_>=_{n}"
                fig.add_trace(go.Scatter(
                    x=stats["Month"], 
                    y=stats[column],
                    mode='lines+markers+text',
                    name=f'Users ≥ {n} Bookings',
                    text=stats[column],
                    textposition='top center',
                    yaxis='y'
                ))
            
            fig.add_trace(go.Bar(
                x=stats["Month"], 
                y=total_bookings,
                name='Total Bookings',
                opacity=0.3,
                yaxis='y2',
                text=total_bookings,
                textposition='outside',
                marker_color='rgb(64, 105, 225)'
            ))
            
            fig.update_layout(
                title=dict(
                    text=f'Monthly User Booking Analysis ({start_period} to {end_period})',
                    x=0.5,
                    xanchor='center',
                    font=dict(size=20)
                ),
                xaxis_title='Month',
                yaxis=dict(
                    title='Number of Users',
                    side='left',
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='rgba(0,0,0,0.1)'
                ),
                yaxis2=dict(
                    title='Total Bookings',
                    side='right',
                    overlaying='y',
                    showgrid=False
                ),
                height=600,
                showlegend=True,
                legend=dict(
                    x=1.05,
                    y=1,
                    xanchor='left',
                    yanchor='top',
                    bgcolor='rgba(255, 255, 255, 0.8)',
                    bordercolor='rgba(0, 0, 0, 0.2)',
                    borderwidth=1
                ),
                margin=dict(r=150),
                plot_bgcolor='white',
                paper_bgcolor='white',
                xaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='rgba(0,0,0,0.1)'
                )
            )
            
            return (fig, {'display': 'block'}, "Analysis completed successfully", 
                    "text-green-600", export_data.to_json(date_format='iso', orient='split'))
        
        except Exception as e:
            return dash.no_update, {'display': 'none'}, f"Error: {str(e)}", "text-red-600", None

    @app.callback(
        Output("download-monthly-xlsx", "data"),
        Input("export-monthly-btn", "n_clicks"),
        State("chart-data-monthly", "data"),
        prevent_initial_call=True
    )
    def export_chart_data(n_clicks, chart_data):
        if not n_clicks or not chart_data:
            raise PreventUpdate
        
        try:
            df = pd.read_json(StringIO(chart_data), orient='split')
            return dcc.send_data_frame(df.to_excel, 
                                     "monthly_booking_analysis.xlsx", 
                                     sheet_name="Monthly Analysis",
                                     index=False)
        except Exception:
            raise PreventUpdate