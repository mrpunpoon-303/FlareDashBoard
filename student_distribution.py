from dash import html, dcc, Input, Output, State
from dash.exceptions import PreventUpdate
import pandas as pd
from io import StringIO
import matplotlib.pyplot as plt
from matplotlib_venn import venn3
import re
import base64
import io

def create_student_distribution_layout(show_upload=True):
    return html.Div([
        dcc.Download(id="download-venn-excel"),
        html.H1("Student Distribution Analysis", className="text-2xl font-bold mb-4"),
        html.Div([
            html.Div([
                html.Label('Start Period:', className="block mb-2 font-medium"),
                dcc.Dropdown(id='start-period-dist', className="w-full")
            ], className="w-1/2 pr-2"),
            html.Div([
                html.Label('End Period:', className="block mb-2 font-medium"),
                dcc.Dropdown(id='end-period-dist', className="w-full")
            ], className="w-1/2 pl-2")
        ], className="flex mb-4"),
        
        html.Div([
            html.Button('Execute Analysis', id='execute-dist-btn',
                       className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 mr-4"),
            html.Button('Export to Excel', id='export-venn-btn',
                       className="bg-green-500 text-white px-6 py-2 rounded hover:bg-green-600"),
        ], className="flex space-x-4 mb-4"),
        
        html.Div(id='status-message-dist', className="mb-4"),
        html.Div([
            html.Img(id='venn-diagram-img', style={'maxWidth': '600px', 'margin': '0 auto', 'display': 'block'}),
            html.Div(id='details-table', className="mt-4")
        ], id='results-section-dist', style={'display': 'none'}),
        
        dcc.Loading(id="loading-dist", type="default",
                   children=html.Div(id="loading-output-dist"))
    ], className="max-w-7xl mx-auto p-6")

def calculate_distribution(data, start_period, end_period):
    data = data.copy()
    start_month = pd.Period(start_period, freq="M")
    end_month = pd.Period(end_period, freq="M")
    total_months = (pd.period_range(start_month, end_month, freq="M")).size

    data["Start_Date_time"] = pd.to_datetime(data["Start_Date_time"])
    
    filtered_data = data[
        data["Cateory"].notna() & 
        (data["Cateory"] != "Virgin") & 
        (~data["Class_Name"].str.contains("Self Practice", na=False)) &
        (data["Start_Date_time"].dt.to_period("M").astype(str) >= start_period) &
        (data["Start_Date_time"].dt.to_period("M").astype(str) <= end_period)
    ]

    filtered_data["FirstName"] = filtered_data["FirstName"].apply(
        lambda x: re.search(r'\((.*?)\)', x).group(1) if re.search(r'\((.*?)\)', x) else x
    )

    categories = ["Spin", "Sport", "Choreo"]
    sets = {
        cat: set(filtered_data[filtered_data["Cateory"] == cat]["Id_Person"]) 
        for cat in categories
    }

    filtered_data["Month"] = filtered_data["Start_Date_time"].dt.to_period("M")
    bookings_per_student = (
        filtered_data.groupby(["Id_Person", "Month"]).size().reset_index(name="Bookings")
    )
    total_bookings_per_student = (
        bookings_per_student.groupby("Id_Person")["Bookings"].sum().to_dict()
    )

    avg_bookings_per_month = {
        sid: round(total_bookings_per_student[sid] / total_months, 1)
        for sid in total_bookings_per_student
    }

    sizes = {
        "100": sets["Spin"] - sets["Sport"] - sets["Choreo"],
        "010": sets["Sport"] - sets["Spin"] - sets["Choreo"],
        "001": sets["Choreo"] - sets["Spin"] - sets["Sport"],
        "110": (sets["Spin"] & sets["Sport"]) - sets["Choreo"],
        "101": (sets["Spin"] & sets["Choreo"]) - sets["Sport"],
        "011": (sets["Sport"] & sets["Choreo"]) - sets["Spin"],
        "111": sets["Spin"] & sets["Sport"] & sets["Choreo"],
    }

    student_labels = {
        student["Id_Person"]: f"({student['Id_Person']}){student['FirstName']}-{total_bookings_per_student.get(student['Id_Person'], 0)}"
        for _, student in filtered_data[["Id_Person", "FirstName"]].drop_duplicates().iterrows()
    }

    total_students = len(set().union(*sets.values()))

    return categories, sets, sizes, total_students, filtered_data, avg_bookings_per_month, total_bookings_per_student, student_labels

def generate_venn_diagram(categories, sets, sizes, total_students, start_period, end_period):
    fig = plt.figure(figsize=(20, 16))
    gs = plt.GridSpec(2, 1, height_ratios=[6, 1], hspace=0.3)
    plt.subplot(gs[0])

    venn = venn3([sets[cat] for cat in categories], 
                 set_labels=categories,
                 )
    
    for text in venn.set_labels:
        if text:
            text.set_fontsize(30)
            text.set_fontweight('bold')

    for text in venn.subset_labels:
        if text:
            text.set_fontsize(30)

    percentages = {
        key: (len(value) / total_students * 100) if total_students > 0 else 0 
        for key, value in sizes.items()
    }

    for subset in sizes:
        label = venn.get_label_by_id(subset)
        if label:
            label.set_text(f"{len(sizes[subset])}\n({percentages[subset]:.1f}%)")
            label.set_fontsize(30)

    plt.title(f"Student Distribution ({start_period} to {end_period})", pad=20, fontsize=30)

    plt.subplot(gs[1])
    plt.axis('off')
    summary_text = "Student Counts:\n"
    for category in categories:
        count = len(sets[category])
        percentage = (count / total_students * 100) if total_students > 0 else 0
        summary_text += f"{category}: {count} students ({percentage:.2f}%)\n"
    summary_text += f"Total unique students booked in this period: {total_students}"
    plt.text(0.1, 0.5, summary_text, fontsize=30, va='center')

    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight', dpi=200)
    plt.close()
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode()

def create_details_table(filtered_data, sizes, total_students, avg_bookings_per_month, total_bookings_per_student, student_labels):
    bookings_per_student = (
        filtered_data.groupby(["Id_Person", "Month"]).size().reset_index(name="Bookings")
    )
    table_data = []
    categories = ["Spin", "Sport", "Choreo"]
    headers = ["#", "Category", "Percentage", "Avg/Month", "Student", "Retention %", "Avg Booking Retention"]

    subset_order = ["100", "010", "001", "110", "101", "011", "111"]
    subset_names = {
        "100": "Spin",
        "010": "Sport", 
        "001": "Choreo",
        "110": "Spin, Sport",
        "101": "Spin, Choreo",
        "011": "Sport, Choreo",
        "111": "Spin, Sport, Choreo"
    }

    for idx, subset in enumerate(subset_order):
        students = sizes[subset]
        if not students:
            continue

        avg_bookings = round(sum(avg_bookings_per_month.get(sid, 0) for sid in students) / len(students), 1) if students else 0
        retention_students = [sid for sid in students if avg_bookings_per_month.get(sid, 0) >= 2]
        retention_pct = len(retention_students) / len(students) * 100 if students else 0
        avg_booking_retention = round(sum(avg_bookings_per_month.get(sid, 0) for sid in retention_students) / len(retention_students), 1) if retention_students else 0
        student_list = sorted([student_labels[sid] for sid in students])

        table_data.append(html.Tr([
            html.Td(str(idx), className="border px-4 py-2"),
            html.Td(subset_names[subset], className="border px-4 py-2"),
            html.Td(f"{(len(students) / total_students * 100):.1f}%", className="border px-4 py-2 text-center"),
            html.Td(f"{avg_bookings:.1f}", className="border px-4 py-2 text-center"),
            html.Td(", ".join(student_list), className="border px-4 py-2"),
            html.Td(f"{retention_pct:.1f}%", className="border px-4 py-2 text-center"),
            html.Td(f"{avg_booking_retention:.1f}", className="border px-4 py-2 text-center")
        ]))

    return html.Table(
        [html.Thead(
            html.Tr([html.Th(h, className="border px-4 py-2") for h in headers])
        ),
        html.Tbody(table_data)],
        className="w-full border-collapse border"
    )

def create_excel_export(categories, sets, sizes, total_students, filtered_data, avg_bookings_per_month, total_bookings_per_student, student_labels):
    import pandas as pd
    import io
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image
    import base64

    # Create Excel writer object
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Create summary dataframe
    summary_data = []
    for category in categories:
        count = len(sets[category])
        percentage = (count / total_students * 100) if total_students > 0 else 0
        summary_data.append({
            'Category': category,
            'Count': count,
            'Percentage': f"{percentage:.2f}%"
        })
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_excel(writer, sheet_name='Summary', index=False)

    # Create detailed analysis dataframe
    subset_order = ["100", "010", "001", "110", "101", "011", "111"]
    subset_names = {
        "100": "Spin", "010": "Sport", "001": "Choreo",
        "110": "Spin, Sport", "101": "Spin, Choreo",
        "011": "Sport, Choreo", "111": "Spin, Sport, Choreo"
    }

    details_data = []
    for subset in subset_order:
        students = sizes[subset]
        if not students:
            continue

        avg_bookings = round(sum(avg_bookings_per_month.get(sid, 0) for sid in students) / len(students), 1) if students else 0
        retention_students = [sid for sid in students if avg_bookings_per_month.get(sid, 0) >= 2]
        retention_pct = len(retention_students) / len(students) * 100 if students else 0
        avg_booking_retention = round(sum(avg_bookings_per_month.get(sid, 0) for sid in retention_students) / len(retention_students), 1) if retention_students else 0
        student_list = ", ".join(sorted([student_labels[sid] for sid in students]))

        details_data.append({
            'Category': subset_names[subset],
            'Students Count': len(students),
            'Percentage': f"{(len(students) / total_students * 100):.1f}%",
            'Avg Bookings/Month': avg_bookings,
            'Retention %': f"{retention_pct:.1f}%",
            'Avg Booking Retention': avg_booking_retention,
            'Students': student_list
        })

    details_df = pd.DataFrame(details_data)
    details_df.to_excel(writer, sheet_name='Details', index=False)

    writer.close()
    output.seek(0)
    return output.getvalue()

def register_student_distribution_callbacks(app):
    @app.callback(
        [Output('start-period-dist', 'options'),
         Output('end-period-dist', 'options'),
         Output('start-period-dist', 'value'),
         Output('end-period-dist', 'value')],
        Input('shared-stored-data', 'data')
    )
    def update_period_dropdowns(stored_data):
        if not stored_data:
            raise PreventUpdate

        df = pd.read_json(StringIO(stored_data['data']), orient='split')
        periods = sorted(df["Start_Date_time"].dt.to_period("M").astype(str).unique())
        options = [{'label': p, 'value': p} for p in periods]

        return options, options, periods[0], periods[-1]

    @app.callback(
        Output("download-venn-excel", "data"),
        Input("export-venn-btn", "n_clicks"),
        [State('shared-stored-data', 'data'),
         State('start-period-dist', 'value'),
         State('end-period-dist', 'value')],
        prevent_initial_call=True
    )
    def export_venn_to_excel(n_clicks, stored_data, start_period, end_period):
        if not n_clicks or not stored_data:
            raise PreventUpdate

        df = pd.read_json(StringIO(stored_data['data']), orient='split')
        categories, sets, sizes, total_students, filtered_data, avg_bookings_per_month, total_bookings_per_student, student_labels = calculate_distribution(
            df, start_period, end_period
        )

        excel_data = create_excel_export(categories, sets, sizes, total_students, filtered_data, 
                                       avg_bookings_per_month, total_bookings_per_student, student_labels)

        return dcc.send_bytes(excel_data, f"venn_analysis_{start_period}_to_{end_period}.xlsx")

    @app.callback(
        [Output('venn-diagram-img', 'src'),
         Output('details-table', 'children'),
         Output('results-section-dist', 'style'),
         Output('status-message-dist', 'children'),
         Output('status-message-dist', 'className')],
        Input('execute-dist-btn', 'n_clicks'),
        [State('shared-stored-data', 'data'),
         State('start-period-dist', 'value'),
         State('end-period-dist', 'value')]
    )
    def update_distribution(n_clicks, stored_data, start_period, end_period):
        if not n_clicks or not stored_data:
            raise PreventUpdate

        try:
            df = pd.read_json(StringIO(stored_data['data']), orient='split')
            categories, sets, sizes, total_students, filtered_data, avg_bookings_per_month, total_bookings_per_student, student_labels = calculate_distribution(
                df, start_period, end_period
            )

            img_data = generate_venn_diagram(categories, sets, sizes, total_students, start_period, end_period)
            table = create_details_table(filtered_data, sizes, total_students, avg_bookings_per_month, total_bookings_per_student, student_labels)

            return (
                f'data:image/png;base64,{img_data}',
                table,
                {'display': 'block'},
                "Analysis completed successfully",
                "text-green-600"
            )

        except Exception as e:
            return None, None, {'display': 'none'}, f"Error: {str(e)}", "text-red-600"