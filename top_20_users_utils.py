import pandas as pd
import sys

def calculate_top_20(df, start_date, end_date):
    """
    Calculate top 20 users between given date periods with added safety checks
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame containing booking data
    start_date : str
        Start period in 'YYYY-MM' format
    end_date : str
        End period in 'YYYY-MM' format
    
    Returns:
    --------
    pandas.DataFrame
        DataFrame with top 20 users per month
    """
    # Increase recursion limit for safety
    sys.setrecursionlimit(3000)
    
    try:
        # Convert periods to datetime for filtering
        start_date = pd.to_datetime(start_date, format='%Y-%m')
        end_date = pd.to_datetime(end_date, format='%Y-%m')
        
        # Create a copy and exclude "Self Practice"
        data_filtered = df[~df['Class_Name'].str.contains("Self Practice", case=False, na=False)].copy()
        
        # Add month column safely
        data_filtered['Month'] = data_filtered['Start_Date_time'].dt.to_period('M')
        
        # Filter by date range
        filtered_data = data_filtered[
            (data_filtered['Month'].dt.to_timestamp() >= start_date) & 
            (data_filtered['Month'].dt.to_timestamp() <= end_date)
        ]
        
        # Check for empty DataFrame
        if filtered_data.empty:
            return pd.DataFrame(columns=['Month', 'Rank', 'Id_Person', 'FirstName', 'Bookings', 'Formatted'])
        
        # Simplified top 20 calculation
        def get_top_20_for_month(month_data):
            """Get top 20 students for a specific month"""
            # Count bookings per student
            booking_counts = month_data.groupby('Id_Person').size().reset_index(name='Bookings')
            booking_counts = booking_counts.sort_values('Bookings', ascending=False).head(20)
            
            # Get student details
            student_details = month_data[['Id_Person', 'FirstName']].drop_duplicates()
            
            # Merge booking counts with student details
            month_top_20 = booking_counts.merge(
                student_details, 
                on='Id_Person', 
                how='left'
            )
            
            # Add month and rank
            month_top_20['Month'] = month_data['Month'].iloc[0]
            month_top_20['Rank'] = range(1, len(month_top_20) + 1)
            
            return month_top_20
        
        # Process each unique month
        monthly_results = []
        for month in filtered_data['Month'].unique():
            month_data = filtered_data[filtered_data['Month'] == month]
            monthly_top_20 = get_top_20_for_month(month_data)
            monthly_results.append(monthly_top_20)
        
        # Combine results
        if not monthly_results:
            return pd.DataFrame(columns=['Month', 'Rank', 'Id_Person', 'FirstName', 'Bookings', 'Formatted'])
        
        top_20_df = pd.concat(monthly_results, ignore_index=True)
        
        # Format for display
        top_20_df['Formatted'] = (
            top_20_df['FirstName'] + 
            ' (' + top_20_df['Id_Person'].astype(str) + 
            ') : ' + top_20_df['Bookings'].astype(str)
        )
        
        return top_20_df
    
    except Exception as e:
        # Print error for debugging
        print(f"Error in calculate_top_20: {e}")
        import traceback
        traceback.print_exc()
        
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=['Month', 'Rank', 'Id_Person', 'FirstName', 'Bookings', 'Formatted'])

def generate_table_data(top_20_users, selected_students=None, highlight_colors=None):
    """
    Generate table data for Top 20 Users analysis
    
    Parameters:
    -----------
    top_20_users : pandas.DataFrame
        DataFrame with top 20 users
    selected_students : list, optional
        List of students to highlight
    highlight_colors : list, optional
        List of colors for highlighting students
    
    Returns:
    --------
    tuple
        Containing table header and rows
    """
    # Default parameters
    if selected_students is None:
        selected_students = []
    if highlight_colors is None:
        highlight_colors = ['#FFD700', '#ADD8E6', '#90EE90', '#FFA07A']
    
    try:
        # Pivot data for table generation
        pivot_data = top_20_users.pivot_table(
            index='Rank', 
            columns='Month', 
            values='Formatted', 
            aggfunc='first'
        )
        
        # Prepare table header
        table_header = [
            {'name': 'Rank', 'id': 'rank'}
        ] + [
            {'name': col.strftime('%b-%y'), 'id': col.strftime('%b-%y')} 
            for col in pivot_data.columns
        ]
        
        # Prepare table rows
        table_rows = []
        for rank in pivot_data.index:
            row = {'rank': rank}
            
            for month in pivot_data.columns:
                value = pivot_data.loc[rank, month]
                
                # Determine highlight color
                bg_color = "white"
                for idx, student in enumerate(selected_students):
                    if student and student.strip() in str(value):
                        bg_color = highlight_colors[idx]
                        break
                
                # Add month column to row
                row[month.strftime('%b-%y')] = {
                    'value': value if pd.notna(value) else '',
                    'style': {'backgroundColor': bg_color, 'padding': '5px'}
                }
            
            table_rows.append(row)
        
        return table_header, table_rows
    
    except Exception as e:
        # Print error for debugging
        print(f"Error in generate_table_data: {e}")
        import traceback
        traceback.print_exc()
        
        # Return empty header and rows
        return [{'name': 'Rank', 'id': 'rank'}], []