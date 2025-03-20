# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from config import config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(config)

# Initialize MySQL
mysql = MySQL(app)

# User registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Store the new user with plain text password
        cur = mysql.connection.cursor()
        try:
            cur.execute("INSERT INTO Users (username, password, role) VALUES (%s, %s, 'student')",
                        (username, password))
            mysql.connection.commit()
            flash('Registration successful! You can now log in.', 'success')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
        finally:
            cur.close()

        return redirect(url_for('login'))

    return render_template('register.html')  # Registration template

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    if request.method == 'POST':
        # Handle form submission for creating a new event
        event_name = request.form['name']
        event_date = request.form['date']
        event_location = request.form['location']
        event_description = request.form['description']

        # Insert the new event into the database
        cur.execute(
            "INSERT INTO Events (event_name, event_date, location, description, created_by, registration_count, status) VALUES (%s, %s, %s, %s, %s, 0, 'ongoing')",
            (event_name, event_date, event_location, event_description, session['user_id'])
        )
        mysql.connection.commit()
        flash('Event created successfully!', 'success')

    # Fetch all events, including their registration count and status (always fetch fresh data)
    cur.execute("SELECT event_id, event_name, event_date, location, description, status,registration_count FROM Events ORDER BY event_date")
    events = cur.fetchall()

    cur.close()

    return render_template('admin_dashboard.html', events=events)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id, password, role FROM Users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        # Directly compare the plain text passwords
        if user and user[1] == password:
            session['user_id'] = user[0]
            session['role'] = user[2]
            flash('Logged in successfully!', 'success')
            if user[2] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route('/admin/update_event/<int:event_id>', methods=['GET', 'POST'])
def update_event(event_id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        event_name = request.form['name']
        event_date = request.form['date']
        event_description = request.form['description']

        # Update the event in the database
        cur.execute("UPDATE Events SET event_name=%s, event_date=%s, description=%s WHERE event_id=%s",
                    (event_name, event_date, event_description, event_id))
        mysql.connection.commit()
        flash('Event updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    # Fetch the existing event details for the given event_id
    cur.execute("SELECT * FROM Events WHERE event_id = %s", (event_id,))
    event = cur.fetchone()
    cur.close()

    return render_template('update_event.html', event=event)

@app.route('/admin/view_registered_students/<int:event_id>')
def view_registered_students(event_id):
    cur = mysql.connection.cursor()

    # Fetch the event name
    cur.execute("SELECT event_name FROM Events WHERE event_id = %s", (event_id,))
    event = cur.fetchone()
    event_name = event[0] if event else "Unknown Event"  # Extract event name from the result

    # Fetch registered students for the event
    cur.execute("""
        SELECT S.full_name, R.registration_id, R.status, R.registered_at
        FROM Registrations R
        JOIN StudentProfile S ON R.student_id = S.student_id
        WHERE R.event_id = %s
    """, (event_id,))
    registrations = cur.fetchall()

    cur.close()

    return render_template(
        'view_registrations.html',
        event_name=event_name,
        registrations=registrations
    )

@app.route('/register_for_event/<int:event_id>', methods=['POST'])
def register_for_event(event_id):
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))

    student_id = session['user_id']

    cur = mysql.connection.cursor()
    # Register student for the event
    cur.execute("INSERT INTO Registrations (student_id, event_id, status) VALUES (%s, %s, 'registered')",
                (student_id, event_id))

    mysql.connection.commit()
    cur.close()

    # Flash success message and redirect to dashboard
    flash('Successfully registered for the event!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/clear_flash', methods=['POST'])
def clear_flash():
    session.pop('_flashes', None)  # Clear flash messages
    return '', 204  # Return a 204 (No Content) response

@app.route('/')
def home():
    return render_template('home.html')
@app.route('/admin/add_event', methods=['GET', 'POST'])
def add_event():
    if request.method == 'POST':
        # Get form data to create a new event
        event_name = request.form['name']
        event_date = request.form['date']
        event_location = request.form['location']
        event_description = request.form['description']

        # Insert new event into the database
        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO Events (event_name, event_date, location, description, created_by) VALUES (%s, %s, %s, %s, %s)",
                (event_name, event_date, event_location, event_description, session.get('user_id', None))  # Using session's user_id
            )
            mysql.connection.commit()
            flash('Event created successfully!', 'success')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
        finally:
            cur.close()

        return redirect(url_for('admin_dashboard'))  # Redirect back to the admin dashboard after successful event creation

    return render_template('add_event.html')  # If GET request, render the add event page

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()

    # Fetch the most popular event ID using the stored function
    cur.execute("SELECT GetMostPopularEvent();")
    popular_event_id = cur.fetchone()[0]

    if popular_event_id:
        cur.execute("SELECT * FROM Events WHERE event_id = %s", (popular_event_id,))
        most_popular_event_details = cur.fetchone()
    else:
        most_popular_event_details = None

    # Fetch attended events
    cur.execute("""
        SELECT Events.event_id, Events.event_name, Events.event_date, Events.location
        FROM Events
        JOIN Registrations ON Events.event_id = Registrations.event_id
        WHERE Registrations.student_id = %s AND Registrations.status = 'attended'
    """, (user_id,))
    attended_events = cur.fetchall()

    # Fetch registered upcoming events
    cur.execute("""
        SELECT Events.event_id, Events.event_name, Events.event_date, Events.location
        FROM Events
        JOIN Registrations ON Events.event_id = Registrations.event_id
        WHERE Registrations.student_id = %s
          AND Registrations.status = 'registered'
          AND Events.event_date >= %s
    """, (user_id, datetime.now()))
    upcoming_registered_events = cur.fetchall()

    # Fetch unregistered upcoming events
    cur.execute("""
        SELECT Events.event_id, Events.event_name, Events.event_date, Events.location
        FROM Events
        WHERE Events.event_id NOT IN (SELECT event_id FROM Registrations WHERE student_id = %s)
          AND Events.event_date >= %s
    """, (user_id, datetime.now()))
    upcoming_unregistered_events = cur.fetchall()

    # Close the cursor
    cur.close()

    return render_template(
        'student_dashboard.html',
        attended_events=attended_events,
        upcoming_registered_events=upcoming_registered_events,
        upcoming_unregistered_events=upcoming_unregistered_events,
        most_popular_event=most_popular_event_details
    )


@app.route('/mark_attended/<int:event_id>', methods=['POST'])
def mark_attended(event_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE Registrations
        SET status = 'attended'
        WHERE student_id = %s AND event_id = %s
    """, (user_id, event_id))
    mysql.connection.commit()
    cur.close()

    flash('Event marked as attended!', 'success')
    return redirect(url_for('dashboard'))

# Function to suggest the most popular event based on registered count

if __name__ == '__main__':
    app.secret_key = 'your_secret_key'  # Set your secret key
    app.run(debug=True)