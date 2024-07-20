from flask import Flask, request, render_template, send_file, redirect, url_for
import pandas as pd
import io
import csv

app = Flask(__name__, static_url_path='/static')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    if 'file1' not in request.files or 'file2' not in request.files:
        return redirect(request.url)

    file1 = request.files['file1']
    file2 = request.files['file2']

    if file1.filename == '' or file2.filename == '':
        return redirect(request.url)

    try:
       df_groups = pd.read_csv(file1)
       df_hostels = pd.read_csv(file2)
    except Exception as e:
        return f"Error reading CSV files: {e}"

    try:
       result, csv_data = allocate_rooms(df_groups, df_hostels)
    except KeyError as e:
        return f"Missing excepted column in CSV file: {e}"
    except Exception as e:
        return f"Error during room allocation: {e}"

    # Save the CSV data to a file-like object
    output = io.StringIO()
    csv_writer = csv.writer(output)
    csv_writer.writerow(['Group ID', 'Hostel Name', 'Room Number', 'Members Allocated'])
    csv_writer.writerows(csv_data)
    output.seek(0)

    return render_template('result.html', result=result, csv_file=output.getvalue())


@app.route('/download')
def download_file():
    csv_file = request.args.get('csv_file')
    output = io.StringIO(csv_file)
    return send_file(io.BytesIO(output.getvalue().encode()),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='allocation.csv')


def allocate_rooms(groups, hostels):
    allocation = []
    csv_data = []

    if not all(col in groups.columns for col in ['Group ID', 'Members', 'Gender']):
        raise KeyError("Group CSV is missing one or more required columns: 'Group ID', 'Members', 'Gender'")

    # Split groups by gender
    if not all(col in hostels.columns for col in ['Hostel Name', 'Room Number', 'Capacity', 'Gender']):
        raise KeyError("Hostel CSV is missing one or more required columns: 'Hostel Name', 'Room Number', 'Capacity', 'Gender'")


    boys_groups = groups[groups['Gender'].str.contains('Boys')]
    girls_groups = groups[groups['Gender'].str.contains('Girls')]

    boys_hostels = hostels[hostels['Gender'] == 'Boys']
    girls_hostels = hostels[hostels['Gender'] == 'Girls']

        # Allocate rooms for boys and girls
    allocation.extend(allocate_group(boys_groups, boys_hostels))
    allocation.extend(allocate_group(girls_groups, girls_hostels))

        # Format the result and csv data
    for entry in allocation:
        csv_data.append([entry['GroupID'], entry['HostelName'], entry['RoomNumber'], entry['MembersAllocated']])

    return allocation, csv_data


def allocate_group(groups, hostels):
    allocation = []
    hostels = hostels.sort_values(by=['Hostel Name', 'Room Number']).to_dict('records')
    hostel_index = 0

    for _, group in groups.iterrows():
        group_id = group['Group ID']
        members = group['Members']

        while members > 0 and hostel_index < len(hostels):
            hostel = hostels[hostel_index]
            hostel_name = hostel['Hostel Name']
            room_number = hostel['Room Number']
            capacity = hostel['Capacity']

            if members <= capacity:
                allocation.append({
                    'GroupID': group_id,
                    'HostelName': hostel_name,
                    'RoomNumber': room_number,
                    'MembersAllocated': members
                })
                hostels[hostel_index]['Capacity'] -= members
                members = 0
            else:
                allocation.append({
                    'GroupID': group_id,
                    'HostelName': hostel_name,
                    'RoomNumber': room_number,
                    'MembersAllocated': capacity
                })
                members -= capacity
                hostel_index += 1

    return allocation


if __name__ == '__main__':
    app.run(debug=True)

