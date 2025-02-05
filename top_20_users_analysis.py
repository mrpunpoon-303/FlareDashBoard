import dash
from dash import html, dcc, Input, Output, State, dash_table
import pandas as pd
import plotly.express as px
from io import StringIO
from top_20_users_utils import calculate_top_20, generate_table_data

def create_top_20_users_layout(show_upload=True):
    """Create layout for Top 20 Users analysis"""
    return html.Div([
        html.H1("Top 20 Users Analysis", className="text-2xl font-bold mb-4 text-center"),
        
        # Controls Container
        html.Div([
            # Period Selection
            html.Div([
                html.Div([
                    html.Label('Start Period:', className="block mb-2 font-medium"),
                    dcc.Dropdown(
                        id='start-period-top20',
                        className="w-full"
                    )
                ], className="w-1/2 pr-2"),
                
                html.Div([
                    html.Label('End Period:', className="block mb-2 font-medium"),
                    dcc.Dropdown(
                        id='end-period-top20',
                        className="w-full"
                    )
                ], className="w-1/2 pl-2")
            ], className="flex mb-4"),
            
            # Student Selectors
            html.Div([
                html.Div([
                    html.Label(f'Student {i}:', className="block mb-2 font-medium") 
                    for i in range(1, 5)
                ], className="flex justify-between mb-2"),
                html.Div([
                    dcc.Dropdown(
                        id=f'student-selector-top20-{i}',
                        options=[],
                        value=None,
                        className="w-full"
                    )
                    for i in range(1, 5)
                ], className="grid grid-cols-4 gap-4")
            ], className="mb-4"),
            
            # Buttons Row
            html.Div([
                html.Button(
                    'Show Top 20 Users', 
                    id='execute-top20-btn',
                    className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 mr-4"
                ),
                html.Button(
                    'Export Data (XLSX)', 
                    id='export-top20-btn',
                    className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600"
                )
            ], className="mb-4")
        ], id='controls-section-top20', style={'display': 'none'}),
        
        # Status message
        html.Div(id='status-message-top20', className="mb-4"),
        
        # Results Section
        html.Div([
            dash_table.DataTable(
                id='top20-table',
                columns=[],
                data=[],
                style_cell={'textAlign': 'left', 'padding': '5px'},
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[],
                export_format='xlsx'
            )
        ], id='results-section-top20', style={'display': 'none'}),
        
        # Store components
        dcc.Store(id='top20-data'),
        dcc.Download(id="download-top20-xlsx")
    ], className="max-w-7xl mx-auto p-6")

def register_top_20_users_callbacks(app):
    """Register callbacks for Top 20 Users analysis"""
    
    @app.callback(
        [Output('start-period-top20', 'options'),
         Output('end-period-top20', 'options'),
         Output('start-period-top20', 'value'),
         Output('end-period-top20', 'value'),
         Output('student-selector-top20-1', 'options'),
         Output('student-selector-top20-2', 'options'),
         Output('student-selector-top20-3', 'options'),
         Output('student-selector-top20-4', 'options'),
         Output('controls-section-top20', 'style')],
        Input('shared-stored-data', 'data')
    )
    def update_dropdowns(stored_data):
        if not stored_data:
            return ([], [], None, None, 
                    [], [], [], [], 
                    {'display': 'none'})
        
        try:
            # Safely parse the JSON data using StringIO
            df = pd.read_json(StringIO(stored_data['data']), orient='split')
            
            # Prepare period options
            periods = sorted(df["Start_Date_time"].dt.to_period("M").astype(str).unique())
            period_options = [{'label': p, 'value': p} for p in periods]
            
            # Prepare student options
            students = df[['Id_Person', 'FirstName']].drop_duplicates()
            student_options = [
                {'label': f"{row['FirstName']} ({row['Id_Person']})", 
                 'value': f"{row['FirstName']} ({row['Id_Person']})"}
                for _, row in students.iterrows()
            ]
            
            return (period_options, period_options, 
                    periods[0], periods[-1],
                    student_options, student_options, student_options, student_options,
                    {'display': 'block'})
        
        except Exception:
            return ([], [], None, None, 
                    [], [], [], [], 
                    {'display': 'none'})

    @app.callback(
        [Output('top20-table', 'columns'),
         Output('top20-table', 'data'),
         Output('top20-table', 'style_data_conditional'),
         Output('results-section-top20', 'style'),
         Output('status-message-top20', 'children'),
         Output('status-message-top20', 'className'),
         Output('top20-data', 'data')],
        Input('execute-top20-btn', 'n_clicks'),
        [State('shared-stored-data', 'data'),
         State('start-period-top20', 'value'),
         State('end-period-top20', 'value'),
         State('student-selector-top20-1', 'value'),
         State('student-selector-top20-2', 'value'),
         State('student-selector-top20-3', 'value'),
         State('student-selector-top20-4', 'value')]
    )
    def update_top_20_table(n_clicks, stored_data, start_period, end_period, 
                            student1, student2, student3, student4):
        if not n_clicks or not stored_data:
            raise dash.exceptions.PreventUpdate
        
        try:
            # Load data using StringIO
            df = pd.read_json(StringIO(stored_data['data']), orient='split')
            
            # Calculate top 20 users
            top_20_users = calculate_top_20(df, start_period, end_period)
            
            # Check if top_20_users is empty
            if top_20_users.empty:
                return (
                    [], [], [], 
                    {'display': 'block'},
                    "No data found", "text-yellow-600",
                    None
                )
            
            # Get selected students for highlighting
            selected_students = [s for s in [student1, student2, student3, student4] if s]
            
            # Generate table data
            table_header, table_rows = generate_table_data(top_20_users, selected_students)
            
            # Prepare style for conditional formatting
            style_data_conditional = []
            for row in table_rows:
                for col, cell_data in row.items():
                    if isinstance(cell_data, dict) and 'style' in cell_data:
                        style_data_conditional.append({
                            'if': {'filter_query': f'{{rank}} = {row["rank"]} && {{column_id}} = "{col}"'},
                            'backgroundColor': cell_data['style']['backgroundColor']
                        })
            
            return (
                table_header, 
                table_rows, 
                style_data_conditional,
                {'display': 'block'},
                "Analysis completed successfully", "text-green-600",
                top_20_users.to_json(date_format='iso', orient='split')
            )
        
        except Exception as e:
            return (
                [], [], [], 
                {'display': 'none'}, 
                f"Error: {str(e)}", "text-red-600", 
                None
            )

    @app.callback(
        Output("download-top20-xlsx", "data"),
        Input("export-top20-btn", "n_clicks"),
        State("top20-data", "data"),
        prevent_initial_call=True
    )
    def export_top_20_data(n_clicks, top20_data):
        if not n_clicks or not top20_data:
            raise dash.exceptions.PreventUpdate
        
        try:
            # Convert stored data back to DataFrame using StringIO
            top_20_df = pd.read_json(StringIO(top20_data), orient='split')
            
            # Format for export
            export_df = top_20_df.copy()
            export_df['Month'] = export_df['Month'].astype(str)
            
            return dcc.send_data_frame(
                export_df.to_excel, 
                "top_20_users.xlsx", 
                sheet_name="Top 20 Users",
                index=False
            )
        except Exception:
            raise dash.exceptions.PreventUpdate