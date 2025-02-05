from dash import dcc, html
import dash_bootstrap_components as dbc

def create_layout(show_upload=True):
    return html.Div([
        # Main container
        html.Div([
            html.H1("Booking Frequency Analysis", className="text-2xl font-bold mb-6"),
            
            # Controls Section
            html.Div([
                # Analysis Type Selection
                html.Div([
                    html.Label("Analysis Type:", className="font-medium mr-4"),
                    dcc.RadioItems(
                        id='analysis-type',
                        options=[
                            {'label': 'Monthly', 'value': 'Monthly'},
                            {'label': 'Range', 'value': 'Range'}
                        ],
                        value='Monthly',
                        className="space-x-4",
                        inputClassName="mr-2"
                    )
                ], className="mb-4"),

                # Period Selection
                html.Div([
                    html.Div(id='period-selector', className="mb-4")
                ], className="mb-4"),

                # Max Upper Bound Input
                html.Div([
                    html.Label("Max Upper Bound:", className="font-medium mr-4"),
                    dcc.Input(
                        id='max-upper',
                        type='number',
                        value=15,
                        min=1,
                        className="border rounded p-1 w-24"
                    )
                ], className="mb-4"),

                # Run Analysis Button
                html.Button(
                    "Run Analysis",
                    id="run-analysis",
                    className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 mb-4"
                ),
            ], className="mb-6"),

            # Status message
            html.Div(id='status-message', className="mb-4"),

            # Results Section (initially hidden)
            html.Div([
                # Export Button
                html.Div([
                    html.Button(
                        "Export Data (XLS)", 
                        id="btn-export-data",
                        className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                    )
                ], className="mb-6"),

                # Graph
                dcc.Graph(id='histogram', className="mb-6"),

                # Table
                html.Div(id='table-container', className="overflow-x-auto")
            ], id='results-section', style={'display': 'none'})

        ], className="max-w-7xl mx-auto p-6"),

        # Loading components
        dcc.Loading(
            id="loading-analysis",
            type="default",
            children=html.Div(id="analysis-output")
        ),
        
        # Download component
        dcc.Download(id="download-xlsx")
        
    ], className="p-4")