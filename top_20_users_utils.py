import pandas as pd
import logging
import traceback
from typing import Optional, List, Dict, Any
from datetime import datetime
from dateutil.relativedelta import relativedelta

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def safe_process_data(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    return wrapper

@safe_process_data
def format_class_details(row: pd.Series) -> str:
    try:
        details = []
        for idx, (cls, date, teacher) in enumerate(zip(
            row['ClassList'], 
            row['DateList'], 
            row['TeacherList']
        )):
            details.append(f"{idx + 1}. {cls} | {date} | {teacher}")
        return '<br>'.join(details)
    except Exception as e:
        logger.error(f"Error formatting class details: {str(e)}")
        return "Error displaying details"

def calculate_top_20(df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    try:
        logger.info(f"Starting calculate_top_20 for period {start_date} to {end_date}")
        
        if df.empty:
            return pd.DataFrame()
        
        required_columns = ['Start_Date_time', 'Id_Person', 'FirstName', 'Class_Name', 'Teacher']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Convert dates and include full end month
        try:
            start_date = pd.to_datetime(start_date + '-01')
            end_date = pd.to_datetime(end_date + '-01')
            end_date = end_date + relativedelta(months=1) - relativedelta(days=1)  # Last day of end month
        except Exception as e:
            raise ValueError("Invalid date format")

        data_filtered = df.copy()
        
        if not pd.api.types.is_datetime64_any_dtype(data_filtered['Start_Date_time']):
            data_filtered['Start_Date_time'] = pd.to_datetime(data_filtered['Start_Date_time'])
        
        # Filter data including the end month
        mask = (data_filtered['Start_Date_time'] >= start_date) & (data_filtered['Start_Date_time'] <= end_date)
        data_filtered = data_filtered[mask]
        
        # Filter out Self Practice
        data_filtered = data_filtered[~data_filtered['Class_Name'].str.contains("Self Practice", case=False, na=False)]
        
        # Create Month and FullName columns
        data_filtered['Month'] = data_filtered['Start_Date_time'].dt.strftime('%Y-%m')
        data_filtered['FullName'] = data_filtered.apply(
            lambda x: f"{x['FirstName']} ({x['Id_Person']})", axis=1
        )
        
        # Process each month
        all_results = []
        unique_months = sorted(data_filtered['Month'].unique())
        
        for month in unique_months:
            month_data = data_filtered[data_filtered['Month'] == month]
            
            grouped = month_data.groupby('FullName').agg(
                Bookings=('FullName', 'count'),
                ClassList=('Class_Name', lambda x: x.dropna().tolist()),
                DateList=('Start_Date_time', lambda x: x.dropna().dt.strftime('%Y-%m-%d').tolist()),
                TeacherList=('Teacher', lambda x: x.dropna().tolist())
            ).reset_index()
            
            grouped['ClassList'] = grouped['ClassList'].apply(lambda x: x if x else ["No Data"])
            grouped['DateList'] = grouped['DateList'].apply(lambda x: x if x else ["No Data"])
            grouped['TeacherList'] = grouped['TeacherList'].apply(lambda x: x if x else ["No Data"])
            
            top_20_month = grouped.nlargest(20, 'Bookings', keep='all')
            
            top_20_month['Month'] = month
            top_20_month['Rank'] = range(1, len(top_20_month) + 1)
            
            top_20_month['Formatted'] = top_20_month['FullName'] + ' : ' + top_20_month['Bookings'].astype(str)
            top_20_month['ClassDetails'] = top_20_month.apply(format_class_details, axis=1)
            
            all_results.append(top_20_month)
        
        if not all_results:
            return pd.DataFrame()
        
        final_df = pd.concat(all_results, ignore_index=True)
        final_df = final_df.sort_values(['Month', 'Rank'])
        
        logger.info("Successfully completed calculate_top_20")
        return final_df
        
    except Exception as e:
        logger.error(f"Error in calculate_top_20: {str(e)}")
        logger.error(traceback.format_exc())
        return pd.DataFrame()