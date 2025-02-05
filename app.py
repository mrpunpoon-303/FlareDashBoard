from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from layouts import create_layout
from callbacks import register_callbacks
from monthly_user_booking_analysis import (
    create_monthly_user_booking_layout, 
    register_monthly_user_booking_callbacks
)
from MonthlyStatBooking import (
    create_monthly_stat_layout,
    register_monthly_stat_callbacks
)
from monthly_booking_student_layout import create_monthly_booking_student_layout
from monthly_booking_student_callbacks import register_monthly_booking_student_callbacks
from top_20_users_analysis import (
    create_top_20_users_layout,
    register_top_20_users_callbacks
)
from utils import parse_contents

app = Dash(__name__, 
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        'https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css'
    ],
    suppress_callback_exceptions=True
)

# Define the main app layout with navigation and shared file upload
app.layout = html.Div([
    # File Upload Section (Shared)
    html.Div([
        dcc.Upload(
            id='shared-upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select Excel File', className="text-blue-500 hover:text-blue-700")
            ]),
            className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-gray-400",
            multiple=False
        ),
        # Add loading wrapper
        dcc.Loading(
            id="loading-upload",
            type="circle",
            children=[
                html.Div(id='shared-upload-feedback', className="mt-2 text-sm"),
                html.Div(id="loading-upload-output")  # Hidden div for loading state
            ]
        )
    ], className="max-w-4xl mx-auto p-6"),
    
    # Navigation
    html.Div([
        dcc.Link('Booking Frequency', href='/'),
        html.Span(' | ', className="mx-2"),
        dcc.Link('Students Booking Analysis', href='/monthly-user-booking'),
        html.Span(' | ', className="mx-2"),
        dcc.Link('Monthly Statistics', href='/monthly-stats'),
        html.Span(' | ', className="mx-2"),
        dcc.Link('Monthly Booking by Student', href='/student-booking'),
        html.Span(' | ', className="mx-2"),
        dcc.Link('Top 20 Users', href='/top-20-users'),
    ], className="bg-gray-100 p-4 flex justify-center space-x-4"),
    
    # Page content container
    html.Div(id='page-content'),

    # Shared data store
    dcc.Store(id='shared-stored-data', storage_type='memory'),
    dcc.Store(id='url', storage_type='memory'),
    dcc.Location(id='url-location', refresh=False)
])

# Callback to handle shared file upload
@app.callback(
    [Output('shared-stored-data', 'data'),
     Output('shared-upload-feedback', 'children'),
     Output('shared-upload-feedback', 'className'),
     Output('loading-upload-output', 'children')],  # Add output for loading state
    Input('shared-upload-data', 'contents'),
    State('shared-upload-data', 'filename')
)
def store_shared_data(contents, filename):
    if contents is None:
        return None, "", "", ""
    
    df, error = parse_contents(contents)
    if error:
        return None, f"Error: {error}", "mt-2 text-red-600", ""
    
    return {
        'data': df.to_json(date_format='iso', orient='split'),
        'filename': filename
    }, f"File uploaded: {filename}", "mt-2 text-green-600", ""

# Callback to handle page routing
@app.callback(
    Output('page-content', 'children'),
    Input('url-location', 'pathname')
)
def display_page(pathname):
    if pathname == '/monthly-user-booking':
        return create_monthly_user_booking_layout(show_upload=False)
    elif pathname == '/monthly-stats':
        return create_monthly_stat_layout(show_upload=False)
    elif pathname == '/student-booking':
        return create_monthly_booking_student_layout(show_upload=False)
    elif pathname == '/top-20-users':
        return create_top_20_users_layout(show_upload=False)
    else:
        return create_layout(show_upload=False)

# Register callbacks
register_callbacks(app)
register_monthly_user_booking_callbacks(app)
register_monthly_stat_callbacks(app)
register_monthly_booking_student_callbacks(app)
register_top_20_users_callbacks(app)

if __name__ == '__main__':
    app.run_server(debug=True, port=8062)