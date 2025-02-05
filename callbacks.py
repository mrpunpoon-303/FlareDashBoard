from dash import Input, Output, State, dash_table, html, dcc
from dash.exceptions import PreventUpdate
from dash import ALL
import plotly.graph_objects as go
import pandas as pd
from io import StringIO
import dash

from utils import (
    create_frequency_table, 
    get_monthly_selector, 
    get_range_selector
)

def register_callbacks(app):
    @app.callback(
        Output('period-selector', 'children'),
        [Input('shared-stored-data', 'data'),
         Input('analysis-type', 'value')]
    )
    def update_period_selector(stored_data, analysis_type):
        if not stored_data:
            raise PreventUpdate

        data = pd.read_json(StringIO(stored_data['data']), orient='split')
        periods = sorted(data["Start_Date_time"].dt.to_period("M").astype(str).unique())
        return get_monthly_selector(periods) if analysis_type == 'Monthly' else get_range_selector(periods)

    @app.callback(
        [Output('histogram', 'figure'),
         Output('table-container', 'children'),
         Output('results-section', 'style'),
         Output('status-message', 'children'),
         Output('status-message', 'className'),
         Output('analysis-output', 'children')],
        Input('run-analysis', 'n_clicks'),
        [State('shared-stored-data', 'data'),
         State('analysis-type', 'value'),
         State('max-upper', 'value'),
         State({'type': 'period', 'mode': ALL}, 'value')]
    )
    def update_outputs(n_clicks, stored_data, analysis_type, max_upper, period_values):
        if not n_clicks or not stored_data:
            raise PreventUpdate

        try:
            data = pd.read_json(StringIO(stored_data['data']), orient='split')
            
            if analysis_type == 'Monthly':
                period_value = period_values[0] if period_values else None
                if not period_value:
                    raise ValueError("Please select a period")
                table = create_frequency_table(data, period=period_value, max_upper=max_upper)
            else:
                if len(period_values) < 2:
                    raise ValueError("Please select start and end periods")
                table = create_frequency_table(data, start_period=period_values[0], 
                                            end_period=period_values[1], max_upper=max_upper)

            # Create histogram
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=table["Freq"].astype(str),
                y=table["#Students"],
                text=table["#Students"],
                textposition='auto',
                hovertemplate="<b>Frequency:</b> %{x}<br>" +
                             "<b>Students:</b> %{y}<br>" +
                             "<b>Details:</b> %{customdata}<extra></extra>",
                customdata=table["Details"]
            ))

            # Calculate and add mean and median lines
            freq_data = []
            for freq, count in zip(table["Freq"], table["#Students"]):
                if isinstance(freq, str):
                    freq = int(freq.replace('>', ''))
                freq_data.extend([freq] * count)

            if freq_data:
                mean_val = sum(freq_data) / len(freq_data)
                median_val = sorted(freq_data)[len(freq_data)//2]
                
                fig.add_vline(x=mean_val, line_dash="dash", line_color="red",
                             annotation_text=f"Mean: {mean_val:.2f}",
                             annotation_position="top right",
                             annotation_y=1.1)
                
                fig.add_vline(x=median_val, line_dash="dash", line_color="green",
                             annotation_text=f"Median: {median_val:.2f}",
                             annotation_position="bottom right",
                             annotation_y=0.9)

            # Create title with date range
            title = 'Booking Frequency Distribution'
            if analysis_type == 'Monthly':
                title += f' ({period_values[0]})'
            else:
                title += f' ({period_values[0]} to {period_values[1]})'
                
            fig.update_layout(
                title=title,
                xaxis_title='Frequency of Bookings',
                yaxis_title='Number of Students',
                height=500
            )

            # Create table
            table_component = html.Table([
                html.Thead(
                    html.Tr([
                        html.Th(col, className="p-3 text-left font-medium text-gray-600 border") 
                        for col in table.columns
                    ], className="bg-gray-50")
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(row[col], className="p-3 border") 
                        for col in table.columns
                    ], className="hover:bg-gray-50")
                    for _, row in table.iterrows()
                ])
            ], className="min-w-full divide-y divide-gray-200")

            return fig, table_component, {'display': 'block'}, "Analysis completed successfully", "text-green-600", ""

        except Exception as e:
            return dash.no_update, dash.no_update, {'display': 'none'}, f"Error: {str(e)}", "text-red-600", ""

    @app.callback(
        Output("download-xlsx", "data"),
        Input("btn-export-data", "n_clicks"),
        [State('shared-stored-data', 'data'),
         State('analysis-type', 'value'),
         State('max-upper', 'value'),
         State({'type': 'period', 'mode': ALL}, 'value')],
        prevent_initial_call=True
    )
    def export_data(n_clicks, stored_data, analysis_type, max_upper, period_values):
        if not n_clicks or not stored_data:
            raise PreventUpdate

        try:
            data = pd.read_json(StringIO(stored_data['data']), orient='split')
            if analysis_type == 'Monthly':
                period_value = period_values[0] if period_values else None
                if not period_value:
                    raise PreventUpdate
                table = create_frequency_table(data, period=period_value, max_upper=max_upper)
            else:
                if len(period_values) < 2:
                    raise PreventUpdate
                table = create_frequency_table(data, start_period=period_values[0], 
                                            end_period=period_values[1], max_upper=max_upper)

            if table is None:
                raise PreventUpdate

            return dcc.send_data_frame(table.to_excel, "booking_frequency.xlsx", sheet_name="Frequency Analysis")
        except Exception:
            raise PreventUpdate