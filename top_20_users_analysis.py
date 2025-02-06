import dash
from dash import html, dcc, Input, Output, State, no_update
import pandas as pd
from io import StringIO
from top_20_users_utils import calculate_top_20
import traceback
import openpyxl
import os

def create_top_20_users_layout(show_upload=True):
    return html.Div([
        html.H1("Top 20 Users Analysis", className="text-2xl font-bold mb-4 text-center"),
        
        html.Div([
            html.Div([
                html.Div([
                    html.Label('Start Period:', className="block mb-2 font-medium"),
                    dcc.Dropdown(id='start-period-top20', className="w-full")
                ], className="w-1/2 pr-2"),
                
                html.Div([
                    html.Label('End Period:', className="block mb-2 font-medium"),
                    dcc.Dropdown(id='end-period-top20', className="w-full")
                ], className="w-1/2 pl-2")
            ], className="flex mb-4"),
            
            html.Div([
                html.Div([
                    html.Label(f'Student {i}:', className="block mb-2 font-medium") 
                    for i in range(1, 5)
                ], className="grid grid-cols-4 gap-4 mb-2"),
                html.Div([
                    dcc.Dropdown(
                        id=f'student-selector-top20-{i}',
                        options=[{'label': 'None', 'value': 'None'}],
                        value='None',
                        className="w-full"
                    ) for i in range(1, 5)
                ], className="grid grid-cols-4 gap-4")
            ], className="mb-4"),
            
            html.Div([
                html.Div([
                    dcc.Loading(
                        id="loading-top20-table",
                        type="circle",
                        children=[
                            html.Button(
                                'Show Top 20 Users', 
                                id='execute-top20-btn',
                                className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 mr-4"
                            ),
                            html.Div(id="loading-top20-output")
                        ]
                    ),
                ], className="mr-4"),
                html.Button(
                    'Export Data (XLSX)', 
                    id='export-top20-btn',
                    className="bg-green-500 text-white px-6 py-2 rounded hover:bg-green-600"
                )
            ], className="flex justify-start mb-4")
        ], id='controls-section-top20', className="mb-6"),
        
        html.Div(id='status-message-top20', className="mb-4"),
        
        dcc.Loading(
            id="loading-top20-data",
            type="circle",
            children=[
                html.Div(
                    className="w-full",
                    children=[
                        html.Div(
                            id='top20-table-container',
                            style={'display': 'none'},
                        )
                    ]
                )
            ]
        ),
        
        dcc.Store(id='top20-data'),
        dcc.Download(id="download-top20-xlsx")
    ], className="container mx-auto p-6")

def register_top_20_users_callbacks(app):
    @app.callback(
        [Output('start-period-top20', 'options'),
         Output('end-period-top20', 'options'),
         Output('start-period-top20', 'value'),
         Output('end-period-top20', 'value'),
         Output('student-selector-top20-1', 'options'),
         Output('student-selector-top20-2', 'options'),
         Output('student-selector-top20-3', 'options'),
         Output('student-selector-top20-4', 'options'),
         Output('controls-section-top20', 'style'),
         Output('loading-top20-output', 'children')],
        [Input('shared-stored-data', 'data')]
    )
    def update_dropdowns(stored_data):
        if not stored_data:
            return [], [], None, None, [], [], [], [], {'display': 'none'}, ''
        
        try:
            df = pd.read_json(StringIO(stored_data['data']), orient='split')
            df['Start_Date_time'] = pd.to_datetime(df['Start_Date_time'])
            
            periods = sorted(df['Start_Date_time'].dt.strftime('%Y-%m').unique())
            period_options = [{'label': p, 'value': p} for p in periods]
            
            students = df[['Id_Person', 'FirstName']].drop_duplicates()
            student_options = [{'label': 'None', 'value': 'None'}] + [
                {'label': f"{row['FirstName']} ({row['Id_Person']})", 
                 'value': f"{row['FirstName']} ({row['Id_Person']})"}
                for _, row in students.iterrows()
            ]
            
            return (period_options, period_options,
                    periods[0], periods[-1],
                    student_options, student_options, student_options, student_options,
                    {'display': 'block'}, '')
        except Exception as e:
            print(f"Error in update_dropdowns: {str(e)}")
            print(traceback.format_exc())
            return [], [], None, None, [], [], [], [], {'display': 'none'}, ''

    @app.callback(
        [Output('top20-table-container', 'children'),
         Output('top20-table-container', 'style'),
         Output('status-message-top20', 'children'),
         Output('status-message-top20', 'className'),
         Output('top20-data', 'data')],
        [Input('execute-top20-btn', 'n_clicks'),
         Input('student-selector-top20-1', 'value'),
         Input('student-selector-top20-2', 'value'),
         Input('student-selector-top20-3', 'value'),
         Input('student-selector-top20-4', 'value')],
        [State('shared-stored-data', 'data'),
         State('start-period-top20', 'value'),
         State('end-period-top20', 'value')]
    )
    def update_top_20_table(n_clicks, student1, student2, student3, student4,
                           stored_data, start_period, end_period):
        if not n_clicks or not stored_data or not start_period or not end_period:
            return no_update, no_update, no_update, no_update, no_update
        
        try:
            df = pd.read_json(StringIO(stored_data['data']), orient='split')
            top_20_users = calculate_top_20(df, start_period, end_period)
            
            if top_20_users.empty:
                return None, {'display': 'none'}, "No data found for selected period", "text-yellow-600", None
            
            selected_students = [s for s in [student1, student2, student3, student4] 
                               if s and s != 'None']
            
            highlight_colors = ['#FFD700', '#ADD8E6', '#90EE90', '#FFA07A']
            
            pivot_data = top_20_users.pivot(
                index='Rank',
                columns='Month',
                values='Formatted'
            ).reset_index()
            
            pivot_details = top_20_users.pivot(
                index='Rank',
                columns='Month',
                values='ClassDetails'
            )
            
            formatted_columns = ['Rank']
            for col in pivot_data.columns[1:]:
                try:
                    date = pd.to_datetime(str(col) + '-01')
                    formatted_columns.append(date.strftime('%b %Y'))
                except:
                    formatted_columns.append(col)
            
            table_html = html.Table([
                html.Thead(
                    html.Tr([
                        html.Th(col, style={
                            'backgroundColor': '#f8f9fa',
                            'padding': '8px',
                            'borderBottom': '2px solid #dee2e6',
                            'textAlign': 'center',
                            'fontSize': '12px',
                            'minWidth': '40px' if col == 'Rank' else '120px',
                            'maxWidth': '40px' if col == 'Rank' else '120px'
                        }) for col in formatted_columns
                    ])
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(
                            str(row['Rank']), 
                            style={
                                'textAlign': 'center',
                                'fontWeight': 'bold',
                                'padding': '6px',
                                'borderBottom': '1px solid #dee2e6',
                                'backgroundColor': '#f8f8f8' if int(row['Rank']) % 2 == 0 else 'white',
                                'fontSize': '12px'
                            }
                        ),
                        *[
                            html.Td(
                                str(row[col]) if pd.notna(row[col]) else "",
                                title=str(pivot_details.loc[row['Rank'], col]).replace('<br>', '\n') if pd.notna(pivot_details.loc[row['Rank'], col]) else "",
                                style={
                                    'backgroundColor': next(
                                        (highlight_colors[i] for i, student in enumerate(selected_students)
                                         if student in str(row[col])),
                                        '#f8f8f8' if int(row['Rank']) % 2 == 0 else 'white'
                                    ),
                                    'padding': '6px',
                                    'borderBottom': '1px solid #dee2e6',
                                    'fontSize': '12px',
                                    'whiteSpace': 'normal',
                                    'maxWidth': '120px',
                                    'overflow': 'hidden',
                                    'textOverflow': 'ellipsis'
                                }
                            ) for col in pivot_data.columns[1:]
                        ]
                    ]) for _, row in pivot_data.iterrows()
                ])
            ], style={
                'width': '100%',
                'borderCollapse': 'collapse',
                'border': '1px solid #dee2e6',
                'tableLayout': 'fixed'
            })
            
            return (
                table_html,
                {'display': 'block'},
                "Analysis completed successfully",
                "text-green-600",
                top_20_users.to_json(date_format='iso', orient='split')
            )
            
        except Exception as e:
            print(f"Error in update_top_20_table: {str(e)}")
            print(traceback.format_exc())
            return (
                None,
                {'display': 'none'},
                f"Error: {str(e)}",
                "text-red-600",
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
            df = pd.read_json(StringIO(top20_data), orient='split')
            
            # Create pivot tables for both data and tooltips
            pivot_data = df.pivot(
                index='Rank',
                columns='Month',
                values='Formatted'
            ).reset_index()
            
            pivot_tooltips = df.pivot(
                index='Rank',
                columns='Month',
                values='ClassDetails'
            ).reset_index()
            
            # Format column headers
            for col in pivot_data.columns:
                if col != 'Rank':
                    try:
                        date = pd.to_datetime(str(col) + '-01')
                        new_col = date.strftime('%b %Y')
                        pivot_data.rename(columns={col: new_col}, inplace=True)
                        pivot_tooltips.rename(columns={col: new_col}, inplace=True)
                    except:
                        continue
            
            # Create Excel writer with engine specification
            with pd.ExcelWriter("temp.xlsx", engine='openpyxl') as writer:
                pivot_data.to_excel(writer, sheet_name="Top 20 Users", index=False)
                
                # Get the worksheet
                worksheet = writer.sheets["Top 20 Users"]
                
                # Add comments to cells
                for row in range(len(pivot_data)):
                    for col in range(1, len(pivot_data.columns)):  # Skip Rank column
                        cell = worksheet.cell(row=row + 2, column=col + 1)  # +2 for header and 1-based indexing
                        tooltip = str(pivot_tooltips.iloc[row, col])
                        if tooltip != 'nan':
                            cell.comment = openpyxl.comments.Comment(
                                tooltip.replace('<br>', '\n'),
                                'System'
                            )
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column = list(column)
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
            
            # Read the file and return
            with open("temp.xlsx", "rb") as f:
                encoded = f.read()
            
            os.remove("temp.xlsx")  # Clean up temp file
            
            return dcc.send_bytes(encoded, "top_20_users.xlsx")
        
        except Exception as e:
            print(f"Export error: {str(e)}")
            print(traceback.format_exc())
            return no_update