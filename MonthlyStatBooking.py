from dash import html, dcc, Input, Output, State
import pandas as pd
import plotly.graph_objs as go
from dash.exceptions import PreventUpdate
from io import StringIO
import dash

def calculate_monthly_stats(data, exclude_single_bookings=False):
    """Calculate monthly statistics from the data"""
    data = data.copy()
    data["YearMonth"] = data["Start_Date_time"].dt.to_period("M")
    
    # Exclude "Self Practice" classes
    data = data[~data["Class_Name"].str.contains("Self Practice", case=False, na=False)]
    
    booking_frequencies = data.groupby(["YearMonth", "Id_Person"]).size().reset_index(name="Bookings")
    
    if exclude_single_bookings:
        booking_frequencies = booking_frequencies[booking_frequencies["Bookings"] > 1]
    
    # Calculate statistics
    stats = booking_frequencies.groupby("YearMonth")["Bookings"].agg(["mean", "median"]).reset_index()
    stats["Total"] = booking_frequencies.groupby("YearMonth")["Bookings"].sum().values
    stats["Students"] = booking_frequencies.groupby("YearMonth")["Id_Person"].nunique().values
    stats["YearMonth"] = stats["YearMonth"].astype(str)
    
    return stats

def create_monthly_stat_layout(show_upload=True):
    """Create the layout for monthly statistics analysis"""
    return html.Div([
        html.H1("Monthly Booking Statistics Analysis", className="text-2xl font-bold mb-4 text-center"),
        
        # Controls Container
        html.Div([
            # Period Selection
            html.Div([
                html.Div([
                    html.Label('Start Period:', className="block mb-2 font-medium"),
                    dcc.Dropdown(
                        id='start-period-stats',
                        className="w-full"
                    )
                ], className="w-1/2 pr-2"),
                
                html.Div([
                    html.Label('End Period:', className="block mb-2 font-medium"),
                    dcc.Dropdown(
                        id='end-period-stats',
                        className="w-full"
                    )
                ], className="w-1/2 pl-2")
            ], className="flex mb-4"),
            
            # Exclude Single Bookings Checkbox
            html.Div([
                dcc.Checklist(
                    id='exclude-single-bookings',
                    options=[{'label': 'Exclude Single Bookings', 'value': True}],
                    className="mr-2"
                )
            ], className="mb-4"),
            
            # Buttons Row
            html.Div([
                html.Button(
                    'Execute Analysis', 
                    id='execute-stats-btn',
                    className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 mr-4"
                ),
                html.Button(
                    'Export Data (XLSX)', 
                    id='export-stats-btn',
                    className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600"
                )
            ], className="mb-4")
        ], id='controls-section-stats', style={'display': 'none'}),
        
        # Status message
        html.Div(id='status-message-stats', className="mb-4"),
        
        # Results Section
        html.Div([
            dcc.Graph(id='stats-graph'),
            dcc.Graph(id='students-graph')
        ], id='results-section-stats', style={'display': 'none'}),
        
        # Store components
        dcc.Store(id='chart-data-stats'),
        dcc.Download(id="download-stats-xlsx"),
        dcc.Loading(
            id="loading-stats",
            type="default",
            children=html.Div(id="loading-output-stats")
        )
    ], className="max-w-7xl mx-auto p-6")

def register_monthly_stat_callbacks(app):
    """Register callbacks for monthly statistics analysis"""
    
    @app.callback(
        [Output('start-period-stats', 'options'),
         Output('end-period-stats', 'options'),
         Output('start-period-stats', 'value'),
         Output('end-period-stats', 'value'),
         Output('controls-section-stats', 'style')],
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
        [Output('stats-graph', 'figure'),
         Output('students-graph', 'figure'),
         Output('results-section-stats', 'style'),
         Output('status-message-stats', 'children'),
         Output('status-message-stats', 'className'),
         Output('chart-data-stats', 'data')],
        Input('execute-stats-btn', 'n_clicks'),
        [State('shared-stored-data', 'data'),
         State('start-period-stats', 'value'),
         State('end-period-stats', 'value'),
         State('exclude-single-bookings', 'value')]
    )
    def update_graphs(n_clicks, stored_data, start_period, end_period, exclude_single_bookings):
        if not n_clicks or not stored_data:
            raise PreventUpdate
            
        try:
            # Load and process data
            df = pd.read_json(StringIO(stored_data['data']), orient='split')
            stats = calculate_monthly_stats(df, exclude_single_bookings)
            
            # Filter by date range
            filtered_stats = stats[
                (stats["YearMonth"] >= start_period) & 
                (stats["YearMonth"] <= end_period)
            ]
            
            # Create main statistics figure
            fig1 = go.Figure()
            
            # Add mean and median lines
            fig1.add_trace(go.Scatter(
                x=filtered_stats["YearMonth"],
                y=filtered_stats["mean"],
                name="Mean",
                mode="lines+markers+text",
                text=[f"{x:.2f}" for x in filtered_stats["mean"]],
                textposition="top center",
                textfont=dict(color='black')
            ))
            
            fig1.add_trace(go.Scatter(
                x=filtered_stats["YearMonth"],
                y=filtered_stats["median"],
                name="Median",
                mode="lines+markers+text",
                text=[f"{x:.2f}" for x in filtered_stats["median"]],
                textposition="bottom center",
                textfont=dict(color='black')
            ))
            
            # Add total bookings bars
            fig1.add_trace(go.Bar(
                x=filtered_stats["YearMonth"],
                y=filtered_stats["Total"],
                name="Total Bookings",
                opacity=0.3,
                text=filtered_stats["Total"].astype(int),
                textposition="outside",
                textfont=dict(color='black'),
                yaxis="y2"
            ))
            
            # Update layout for main figure
            title_suffix = " (Excluding Single Bookings)" if exclude_single_bookings else ""
            fig1.update_layout(
                title=dict(
                    text=f"Monthly Booking Statistics{title_suffix}",
                    x=0.5,
                    xanchor='center',
                    font=dict(size=20)
                ),
                yaxis=dict(
                    title="Mean/Median Value",
                    side="left"
                ),
                yaxis2=dict(
                    title="Total Bookings",
                    side="right",
                    overlaying="y"
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.3,
                    xanchor="center",
                    x=0.5
                ),
                height=400,
                margin=dict(b=100)  # Increased bottom margin to accommodate legend
            )
            
            # Create students figure
            fig2 = go.Figure()
            
            fig2.add_trace(go.Bar(
                x=filtered_stats["YearMonth"],
                y=filtered_stats["Students"],
                text=filtered_stats["Students"].astype(int),
                textposition="outside",
                textfont=dict(color='black')
            ))
            
            # Update layout for students figure
            fig2.update_layout(
                title=dict(
                    text="Number of Students Per Month",
                    x=0.5,
                    xanchor='center',
                    font=dict(size=20)
                ),
                yaxis_title="Number of Students",
                height=400,
                margin=dict(b=50)
            )
            
            return (
                fig1, fig2, {'display': 'block'}, 
                "Analysis completed successfully", "text-green-600",
                filtered_stats.to_json(date_format='iso', orient='split')
            )
            
        except Exception as e:
            return (dash.no_update, dash.no_update, {'display': 'none'}, 
                    f"Error: {str(e)}", "text-red-600", None)
    @app.callback(
        Output("download-stats-xlsx", "data"),
        Input("export-stats-btn", "n_clicks"),
        [State('shared-stored-data', 'data'),
         State('start-period-stats', 'value'),
         State('end-period-stats', 'value'),
         State('exclude-single-bookings', 'value')],
        prevent_initial_call=True
    )
    def export_chart_data(n_clicks, stored_data, start_period, end_period, exclude_single_bookings):
        if not n_clicks or not stored_data:
            raise PreventUpdate
        
        try:
            df = pd.read_json(StringIO(stored_data['data']), orient='split')
            stats = calculate_monthly_stats(df, exclude_single_bookings)
            
            # Filter by date range
            filtered_stats = stats[
                (stats["YearMonth"] >= start_period) & 
                (stats["YearMonth"] <= end_period)
            ]
            
            return dcc.send_data_frame(
                filtered_stats.to_excel,
                "monthly_booking_statistics.xlsx",
                sheet_name="Monthly Statistics",
                index=False
            )
        except Exception:
            raise PreventUpdate