from dash import Input, Output, State, dcc
import pandas as pd
import plotly.graph_objs as go
from dash.exceptions import PreventUpdate
from io import StringIO
import dash
import json

def calculate_monthly_bookings(data, selected_students, start_date, end_date):
    """Calculate monthly bookings for selected students"""
    # Convert date strings to datetime and adjust end date to include the entire month
    start_date = pd.to_datetime(start_date + '-01')
    end_date = pd.to_datetime(end_date + '-01') + pd.offsets.MonthEnd(1)
    
    # Generate all months in the range
    all_months = pd.date_range(start=start_date, end=end_date, freq='MS')
    all_months_str = all_months.strftime('%Y-%m').tolist()
    
    # Filter data by selected students and date range
    data['YearMonth'] = data['Start_Date_time'].dt.strftime('%Y-%m')
    filtered_data = data[
        (data['Id_Person'].isin(selected_students)) &
        (data['Start_Date_time'] >= start_date) &
        (data['Start_Date_time'] <= end_date) &
        (~data['Class_Name'].str.contains('Self Practice', case=False, na=False))
    ]
    
    # Calculate bookings per student per month
    bookings = filtered_data.groupby(['YearMonth', 'Id_Person', 'FirstName']).size().reset_index(name='Bookings')
    
    # Create a DataFrame with all combinations of months and students
    all_combinations = pd.DataFrame([
        (month, student_id, student_name)
        for month in all_months_str
        for student_id, student_name in filtered_data[['Id_Person', 'FirstName']].drop_duplicates().values
    ], columns=['YearMonth', 'Id_Person', 'FirstName'])
    
    # Merge with actual bookings and fill missing values with 0
    result = pd.merge(
        all_combinations,
        bookings,
        on=['YearMonth', 'Id_Person', 'FirstName'],
        how='left'
    ).fillna(0)
    
    return result

def register_monthly_booking_student_callbacks(app):
    """Register callbacks for monthly booking by student analysis"""
    
    @app.callback(
        [Output('student-selector-1', 'options'),
         Output('student-selector-2', 'options'),
         Output('student-selector-3', 'options'),
         Output('student-selector-4', 'options'),
         Output('start-period-student', 'options'),
         Output('end-period-student', 'options'),
         Output('start-period-student', 'value'),
         Output('end-period-student', 'value'),
         Output('controls-section-student', 'style')],
        Input('shared-stored-data', 'data')
    )
    def update_dropdowns(stored_data):
        if not stored_data:
            return [[], [], [], [], [], [], None, None, {'display': 'none'}]
            
        df = pd.read_json(StringIO(stored_data['data']), orient='split')
        
        # Prepare student options
        students = df[['Id_Person', 'FirstName']].drop_duplicates()
        student_options = [
            {'label': f"{row['FirstName']} ({row['Id_Person']})", 
             'value': row['Id_Person']} 
            for _, row in students.iterrows()
        ]
        
        # Prepare period options
        periods = sorted(df['Start_Date_time'].dt.strftime('%Y-%m').unique())
        period_options = [{'label': p, 'value': p} for p in periods]
        
        return (student_options, student_options, student_options, student_options,
                period_options, period_options, periods[0], periods[-1],
                {'display': 'block'})

    @app.callback(
        [Output('student-booking-graph', 'figure'),
         Output('results-section-student', 'style'),
         Output('status-message-student', 'children'),
         Output('status-message-student', 'className'),
         Output('chart-data-student', 'data')],
        Input('execute-student-btn', 'n_clicks'),
        [State('shared-stored-data', 'data'),
         State('student-selector-1', 'value'),
         State('student-selector-2', 'value'),
         State('student-selector-3', 'value'),
         State('student-selector-4', 'value'),
         State('start-period-student', 'value'),
         State('end-period-student', 'value')]
    )
    def update_graph(n_clicks, stored_data, student1, student2, student3, student4,
                    start_period, end_period):
        if not n_clicks or not stored_data:
            raise PreventUpdate
            
        try:
            # Get selected students (remove None values)
            selected_students = [s for s in [student1, student2, student3, student4] if s]
            if not selected_students:
                raise ValueError("Please select at least one student")
                
            # Load data and calculate bookings
            df = pd.read_json(StringIO(stored_data['data']), orient='split')
            bookings = calculate_monthly_bookings(df, selected_students, start_period, end_period)
            
            # Create figure
            fig = go.Figure()
            
            # Add line for each student
            for student_id in selected_students:
                student_data = bookings[bookings['Id_Person'] == student_id]
                student_name = student_data['FirstName'].iloc[0]
                
                fig.add_trace(go.Scatter(
                    x=student_data['YearMonth'],
                    y=student_data['Bookings'],
                    name=f"{student_name} ({student_id})",
                    mode='lines+markers+text',
                    text=student_data['Bookings'].astype(int),
                    textposition='top center'
                ))
            
            # Update layout
            fig.update_layout(
                title=dict(
                    text=f"Monthly Bookings by Student ({start_period} to {end_period})",
                    x=0.5,
                    xanchor='center',
                    font=dict(size=20)
                ),
                xaxis_title="Month",
                yaxis_title="Number of Bookings",
                height=500,
                legend=dict(
                    yanchor="top",
                    y=-0.2,
                    xanchor="center",
                    x=0.5,
                    orientation="h"
                ),
                margin=dict(b=100)  # Add bottom margin for legend
            )
            
            return (
                fig, {'display': 'block'},
                "Analysis completed successfully", "text-green-600",
                bookings.to_json(date_format='iso', orient='split')
            )
            
        except Exception as e:
            return (
                dash.no_update, {'display': 'none'},
                f"Error: {str(e)}", "text-red-600",
                None
            )

    @app.callback(
        Output("download-student-xlsx", "data"),
        Input("export-student-btn", "n_clicks"),
        [State('shared-stored-data', 'data'),
         State('student-selector-1', 'value'),
         State('student-selector-2', 'value'),
         State('student-selector-3', 'value'),
         State('student-selector-4', 'value'),
         State('start-period-student', 'value'),
         State('end-period-student', 'value')],
        prevent_initial_call=True
    )
    def export_chart_data(n_clicks, stored_data, student1, student2, student3, student4,
                         start_period, end_period):
        if not n_clicks or not stored_data:
            raise PreventUpdate
        
        try:
            # Get selected students (remove None values)
            selected_students = [s for s in [student1, student2, student3, student4] if s]
            if not selected_students:
                raise PreventUpdate
                
            # Load data and calculate bookings
            df = pd.read_json(StringIO(stored_data['data']), orient='split')
            bookings = calculate_monthly_bookings(df, selected_students, start_period, end_period)
            
            return dcc.send_data_frame(
                bookings.to_excel,
                "monthly_booking_by_student.xlsx",
                sheet_name="Student Bookings",
                index=False
            )
        except Exception:
            raise PreventUpdate