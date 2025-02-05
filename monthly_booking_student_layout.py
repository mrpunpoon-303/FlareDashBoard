from dash import html, dcc

def create_student_selector(id_suffix, className=""):
    """Create a student dropdown selector"""
    return html.Div([
        html.Label(f'Student {id_suffix}:', className="block mb-2 font-medium"),
        dcc.Dropdown(
            id=f'student-selector-{id_suffix}',
            options=[],
            value=None,
            className=f"w-full {className}"
        )
    ])

def create_monthly_booking_student_layout(show_upload=True):
    """Create the layout for monthly booking by student analysis"""
    return html.Div([
        html.H1("Monthly Booking by Student Analysis", className="text-2xl font-bold mb-4 text-center"),
        
        # Controls Container
        html.Div([
            # Student Selection
            html.Div([
                create_student_selector("1", "mb-2"),
                create_student_selector("2", "mb-2"),
                create_student_selector("3", "mb-2"),
                create_student_selector("4", "mb-2"),
            ], className="grid grid-cols-2 gap-4 mb-4"),
            
            # Period Selection
            html.Div([
                html.Div([
                    html.Label('Start Period:', className="block mb-2 font-medium"),
                    dcc.Dropdown(
                        id='start-period-student',
                        className="w-full"
                    )
                ], className="w-1/2 pr-2"),
                
                html.Div([
                    html.Label('End Period:', className="block mb-2 font-medium"),
                    dcc.Dropdown(
                        id='end-period-student',
                        className="w-full"
                    )
                ], className="w-1/2 pl-2")
            ], className="flex mb-4"),
            
            # Buttons Row
            html.Div([
                html.Button(
                    'Execute Analysis', 
                    id='execute-student-btn',
                    className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 mr-4"
                ),
                html.Button(
                    'Export Data (XLSX)', 
                    id='export-student-btn',
                    className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600"
                )
            ], className="mb-4")
        ], id='controls-section-student'),
        
        # Status message
        html.Div(id='status-message-student', className="mb-4"),
        
        # Results Section
        html.Div([
            dcc.Graph(id='student-booking-graph')
        ], id='results-section-student', style={'display': 'none'}),
        
        # Store components
        dcc.Store(id='chart-data-student'),
        dcc.Download(id="download-student-xlsx"),
        dcc.Loading(
            id="loading-student",
            type="default",
            children=html.Div(id="loading-output-student")
        )
    ], className="max-w-7xl mx-auto p-6")
