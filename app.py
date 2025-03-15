import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room, leave_room

####################################################
# FLASK & DATABASE CONFIGURATION
####################################################
app = Flask(__name__)

# Local MySQL Database Configuration
username = "root"         # Adjust as needed
password = ""     # Adjust as needed
host = "localhost"
database_name = "employeadmin"
# Using PyMySQL as the driver
connection_string = f"mysql+pymysql://{username}:{password}@{host}/{database_name}"
app.config['SQLALCHEMY_DATABASE_URI'] = connection_string
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

####################################################
# MODELS
####################################################
# Common Models
class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name  = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100))
    is_active  = db.Column(db.Boolean, default=True)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(50), default='Employee')

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), default='')
    due_date = db.Column(db.String(50), default='')   # e.g., "dd-mm-yyyy"
    priority = db.Column(db.String(20), default='Medium')
    status = db.Column(db.String(50), default='Open')
    assigned_to = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)

class Shift(db.Model):
    __tablename__ = 'shifts'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    start_time = db.Column(db.String(50), nullable=False)
    end_time = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Active')

class TimeOffRequest(db.Model):
    __tablename__ = 'timeoff_requests'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    start_date = db.Column(db.String(50), nullable=False)
    end_date = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Pending')

class Performance(db.Model):
    __tablename__ = 'performance'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50), default='')  # "YYYY-MM-DD"
    tasks_completed = db.Column(db.Integer, default=0)
    hours_worked = db.Column(db.Integer, default=0)

class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(50), nullable=False)  # "dd-mm-yyyy"
    time = db.Column(db.String(50), nullable=False)  # "hh:mm AM/PM"
    duration = db.Column(db.String(50), default='30 minutes')
    description = db.Column(db.String(500), default='')
    participants = db.Column(db.String(255), default='')
    color = db.Column(db.String(20), default='blue')

# Leave Management Models
class EmployeeLeaveBalance(db.Model):
    __tablename__ = 'employee_leave_balance'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    year = db.Column(db.Integer, default=datetime.now().year)
    annual_remaining = db.Column(db.Float, default=0.0)
    sick_remaining = db.Column(db.Float, default=0.0)
    other_remaining = db.Column(db.Float, default=0.0)
    total_taken = db.Column(db.Float, default=0.0)

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type = db.Column(db.String(20), default='Annual')
    start_date = db.Column(db.String(50), nullable=False)    # "YYYY-MM-DD"
    end_date = db.Column(db.String(50), nullable=False)      # "YYYY-MM-DD"
    days = db.Column(db.Float, default=1.0)
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Compliance (Policy) Models
class PolicyDocument(db.Model):
    __tablename__ = 'policy_documents'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), default='')
    status = db.Column(db.String(50), default='Active')
    doc_url = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PolicyAcknowledgement(db.Model):
    __tablename__ = 'policy_acknowledgements'
    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policy_documents.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    ack_status = db.Column(db.String(50), default='Acknowledged')
    ack_date = db.Column(db.DateTime, default=datetime.utcnow)

# Time Tracking Models
class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.String(50), nullable=False)  # "YYYY-MM-DD"
    is_late = db.Column(db.Boolean, default=False)
    hours_worked = db.Column(db.Float, default=0.0)
    break_time = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Present')

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    progress = db.Column(db.Integer, default=0)  # 0-100

# Communication Model
class Communication(db.Model):
    __tablename__ = 'communications'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Chat Models
class ChatRoom(db.Model):
    __tablename__ = 'chat_rooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatRoomMember(db.Model):
    __tablename__ = 'chat_room_members'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_rooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_rooms.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    content = db.Column(db.String(1000), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

####################################################
# ADMIN ENDPOINTS
####################################################

# --- 1. Admin Dashboard ---
@app.route('/admin/dashboard/summary', methods=['GET'])
def admin_dashboard_summary():
    active_employees = Employee.query.filter_by(is_active=True).count()
    open_tasks = Task.query.filter_by(status='Open').count()
    todays_shifts = Shift.query.filter_by(status='Active').count()
    pending_requests = TimeOffRequest.query.filter_by(status='Pending').count()
    return jsonify({
        "activeEmployees": active_employees,
        "openTasks": open_tasks,
        "todaysShifts": todays_shifts,
        "timeOffRequests": pending_requests
    }), 200

# --- 2. Admin Employee Management ---
@app.route('/admin/employees', methods=['GET'])
def admin_get_employees():
    emps = Employee.query.all()
    data = [{
        "id": e.id,
        "first_name": e.first_name,
        "last_name": e.last_name,
        "department": e.department,
        "is_active": e.is_active,
        "twoFactor": e.two_factor_enabled,
        "role": e.role
    } for e in emps]
    return jsonify(data), 200

@app.route('/admin/employees/<int:employee_id>', methods=['GET'])
def admin_get_employee(employee_id):
    e = Employee.query.get_or_404(employee_id)
    return jsonify({
        "id": e.id,
        "first_name": e.first_name,
        "last_name": e.last_name,
        "department": e.department,
        "is_active": e.is_active,
        "twoFactor": e.two_factor_enabled,
        "role": e.role
    }), 200

@app.route('/admin/employees', methods=['POST'])
def admin_create_employee():
    data = request.get_json()
    required = ["first_name", "last_name", "department"]
    if not data or not all(field in data for field in required):
        return jsonify({"message": "Missing required fields"}), 400
    new_emp = Employee(
        first_name=data["first_name"],
        last_name=data["last_name"],
        department=data["department"],
        is_active=data.get("is_active", True),
        two_factor_enabled=data.get("twoFactor", False),
        role=data.get("role", "Employee")
    )
    db.session.add(new_emp)
    db.session.commit()
    return jsonify({"message": "Employee created", "employee_id": new_emp.id}), 201

@app.route('/admin/employees/<int:employee_id>', methods=['PUT'])
def admin_update_employee(employee_id):
    e = Employee.query.get_or_404(employee_id)
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data"}), 400
    e.first_name = data.get("first_name", e.first_name)
    e.last_name = data.get("last_name", e.last_name)
    e.department = data.get("department", e.department)
    e.is_active = data.get("is_active", e.is_active)
    e.two_factor_enabled = data.get("twoFactor", e.two_factor_enabled)
    e.role = data.get("role", e.role)
    db.session.commit()
    return jsonify({"message": "Employee updated"}), 200

@app.route('/admin/employees/<int:employee_id>', methods=['DELETE'])
def admin_delete_employee(employee_id):
    e = Employee.query.get_or_404(employee_id)
    db.session.delete(e)
    db.session.commit()
    return jsonify({"message": "Employee deleted"}), 200

# --- 3. Admin Communication Management ---
@app.route('/admin/communications', methods=['GET'])
def admin_get_communications():
    comms = Communication.query.order_by(Communication.created_at.desc()).all()
    data = [{"id": c.id, "title": c.title, "message": c.message, "created_at": c.created_at.isoformat()} for c in comms]
    return jsonify(data), 200

@app.route('/admin/communications/<int:comm_id>', methods=['GET'])
def admin_get_communication(comm_id):
    c = Communication.query.get_or_404(comm_id)
    return jsonify({
        "id": c.id,
        "title": c.title,
        "message": c.message,
        "created_at": c.created_at.isoformat()
    }), 200

@app.route('/admin/communications', methods=['POST'])
def admin_create_communication():
    data = request.get_json()
    if not data or "title" not in data or "message" not in data:
        return jsonify({"message": "title and message are required"}), 400
    new_comm = Communication(
        title=data["title"],
        message=data["message"]
    )
    db.session.add(new_comm)
    db.session.commit()
    return jsonify({"message": "Communication created", "comm_id": new_comm.id}), 201

@app.route('/admin/communications/<int:comm_id>', methods=['PUT'])
def admin_update_communication(comm_id):
    c = Communication.query.get_or_404(comm_id)
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data"}), 400
    c.title = data.get("title", c.title)
    c.message = data.get("message", c.message)
    db.session.commit()
    return jsonify({"message": "Communication updated"}), 200

@app.route('/admin/communications/<int:comm_id>', methods=['DELETE'])
def admin_delete_communication(comm_id):
    c = Communication.query.get_or_404(comm_id)
    db.session.delete(c)
    db.session.commit()
    return jsonify({"message": "Communication deleted"}), 200

# --- 4. Admin Scheduling (Events) Management ---
@app.route('/admin/schedule/events', methods=['GET'])
def admin_get_events():
    events = Event.query.order_by(Event.id.desc()).all()
    data = [{
        "id": ev.id,
        "title": ev.title,
        "date": ev.date,
        "time": ev.time,
        "duration": ev.duration,
        "description": ev.description,
        "participants": ev.participants,
        "color": ev.color
    } for ev in events]
    return jsonify(data), 200

@app.route('/admin/schedule/events/<int:event_id>', methods=['GET'])
def admin_get_event(event_id):
    ev = Event.query.get_or_404(event_id)
    return jsonify({
        "id": ev.id,
        "title": ev.title,
        "date": ev.date,
        "time": ev.time,
        "duration": ev.duration,
        "description": ev.description,
        "participants": ev.participants,
        "color": ev.color
    }), 200

@app.route('/admin/schedule/events', methods=['POST'])
def admin_create_event():
    data = request.get_json()
    if not data or not all(k in data for k in ("title", "date", "time")):
        return jsonify({"message": "title, date, and time are required"}), 400
    new_ev = Event(
        title=data["title"],
        date=data["date"],
        time=data["time"],
        duration=data.get("duration", "30 minutes"),
        description=data.get("description", ""),
        participants=data.get("participants", ""),
        color=data.get("color", "blue")
    )
    db.session.add(new_ev)
    db.session.commit()
    return jsonify({"message": "Event created", "event_id": new_ev.id}), 201

@app.route('/admin/schedule/events/<int:event_id>', methods=['PUT'])
def admin_update_event(event_id):
    ev = Event.query.get_or_404(event_id)
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data"}), 400
    ev.title = data.get("title", ev.title)
    ev.date = data.get("date", ev.date)
    ev.time = data.get("time", ev.time)
    ev.duration = data.get("duration", ev.duration)
    ev.description = data.get("description", ev.description)
    ev.participants = data.get("participants", ev.participants)
    ev.color = data.get("color", ev.color)
    db.session.commit()
    return jsonify({"message": "Event updated"}), 200

@app.route('/admin/schedule/events/<int:event_id>', methods=['DELETE'])
def admin_delete_event(event_id):
    ev = Event.query.get_or_404(event_id)
    db.session.delete(ev)
    db.session.commit()
    return jsonify({"message": "Event deleted"}), 200

# --- 5. Admin Time Tracking Management: Attendance ---
@app.route('/admin/time/attendance', methods=['GET'])
def admin_get_attendance():
    records = Attendance.query.order_by(Attendance.date.desc()).all()
    data = [{
        "id": a.id,
        "employee_id": a.employee_id,
        "date": a.date,
        "is_late": a.is_late,
        "hours_worked": a.hours_worked,
        "break_time": a.break_time,
        "status": a.status
    } for a in records]
    return jsonify(data), 200

@app.route('/admin/time/attendance/<int:att_id>', methods=['GET'])
def admin_get_attendance_record(att_id):
    a = Attendance.query.get_or_404(att_id)
    return jsonify({
        "id": a.id,
        "employee_id": a.employee_id,
        "date": a.date,
        "is_late": a.is_late,
        "hours_worked": a.hours_worked,
        "break_time": a.break_time,
        "status": a.status
    }), 200

@app.route('/admin/time/attendance', methods=['POST'])
def admin_create_attendance():
    data = request.get_json()
    required = ["employee_id", "date", "hours_worked", "status"]
    if not data or not all(f in data for f in required):
        return jsonify({"message": "Missing required fields"}), 400
    new_att = Attendance(
        employee_id=data["employee_id"],
        date=data["date"],
        is_late=data.get("is_late", False),
        hours_worked=data["hours_worked"],
        break_time=data.get("break_time", 0.0),
        status=data["status"]
    )
    db.session.add(new_att)
    db.session.commit()
    return jsonify({"message": "Attendance record created", "attendance_id": new_att.id}), 201

@app.route('/admin/time/attendance/<int:att_id>', methods=['PUT'])
def admin_update_attendance(att_id):
    a = Attendance.query.get_or_404(att_id)
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data"}), 400
    a.employee_id = data.get("employee_id", a.employee_id)
    a.date = data.get("date", a.date)
    a.is_late = data.get("is_late", a.is_late)
    a.hours_worked = data.get("hours_worked", a.hours_worked)
    a.break_time = data.get("break_time", a.break_time)
    a.status = data.get("status", a.status)
    db.session.commit()
    return jsonify({"message": "Attendance record updated"}), 200

@app.route('/admin/time/attendance/<int:att_id>', methods=['DELETE'])
def admin_delete_attendance(att_id):
    a = Attendance.query.get_or_404(att_id)
    db.session.delete(a)
    db.session.commit()
    return jsonify({"message": "Attendance record deleted"}), 200

# --- 6. Admin Time Tracking Management: Projects ---
@app.route('/admin/time/projects', methods=['GET'])
def admin_get_projects():
    projects = Project.query.all()
    data = [{"id": p.id, "name": p.name, "progress": p.progress} for p in projects]
    return jsonify(data), 200

@app.route('/admin/time/projects/<int:project_id>', methods=['GET'])
def admin_get_project(project_id):
    p = Project.query.get_or_404(project_id)
    return jsonify({"id": p.id, "name": p.name, "progress": p.progress}), 200

@app.route('/admin/time/projects', methods=['POST'])
def admin_create_project():
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"message": "Project name is required"}), 400
    new_proj = Project(
        name=data["name"],
        progress=data.get("progress", 0)
    )
    db.session.add(new_proj)
    db.session.commit()
    return jsonify({"message": "Project created", "project_id": new_proj.id}), 201

@app.route('/admin/time/projects/<int:project_id>', methods=['PUT'])
def admin_update_project(project_id):
    p = Project.query.get_or_404(project_id)
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data"}), 400
    p.name = data.get("name", p.name)
    p.progress = data.get("progress", p.progress)
    db.session.commit()
    return jsonify({"message": "Project updated"}), 200

@app.route('/admin/time/projects/<int:project_id>', methods=['DELETE'])
def admin_delete_project(project_id):
    p = Project.query.get_or_404(project_id)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"message": "Project deleted"}), 200

# --- 7. Admin Tasks Management ---
@app.route('/admin/tasks', methods=['GET'])
def admin_get_tasks():
    tasks = Task.query.all()
    data = [{
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "due_date": t.due_date,
        "priority": t.priority,
        "status": t.status,
        "assigned_to": t.assigned_to
    } for t in tasks]
    return jsonify(data), 200

@app.route('/admin/tasks/<int:task_id>', methods=['GET'])
def admin_get_task(task_id):
    t = Task.query.get_or_404(task_id)
    return jsonify({
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "due_date": t.due_date,
        "priority": t.priority,
        "status": t.status,
        "assigned_to": t.assigned_to
    }), 200

@app.route('/admin/tasks', methods=['POST'])
def admin_create_task():
    data = request.get_json()
    if not data or "title" not in data:
        return jsonify({"message": "title is required"}), 400
    new_task = Task(
        title=data["title"],
        description=data.get("description", ""),
        due_date=data.get("due_date", ""),
        priority=data.get("priority", "Medium"),
        status=data.get("status", "Open"),
        assigned_to=data.get("assigned_to")
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify({"message": "Task created", "task_id": new_task.id}), 201

@app.route('/admin/tasks/<int:task_id>', methods=['PUT'])
def admin_update_task(task_id):
    t = Task.query.get_or_404(task_id)
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data"}), 400
    t.title = data.get("title", t.title)
    t.description = data.get("description", t.description)
    t.due_date = data.get("due_date", t.due_date)
    t.priority = data.get("priority", t.priority)
    t.status = data.get("status", t.status)
    t.assigned_to = data.get("assigned_to", t.assigned_to)
    db.session.commit()
    return jsonify({"message": "Task updated"}), 200

@app.route('/admin/tasks/<int:task_id>', methods=['DELETE'])
def admin_delete_task(task_id):
    t = Task.query.get_or_404(task_id)
    db.session.delete(t)
    db.session.commit()
    return jsonify({"message": "Task deleted"}), 200

# --- 8. Admin Projects Management (Separate) ---
@app.route('/admin/projects', methods=['GET'])
def admin_get_all_projects():
    projects = Project.query.all()
    data = [{"id": p.id, "name": p.name, "progress": p.progress} for p in projects]
    return jsonify(data), 200

@app.route('/admin/projects/<int:project_id>', methods=['GET'])
def admin_get_single_project(project_id):
    p = Project.query.get_or_404(project_id)
    return jsonify({"id": p.id, "name": p.name, "progress": p.progress}), 200

@app.route('/admin/projects', methods=['POST'])
def admin_create_project_separate():
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"message": "Project name is required"}), 400
    new_proj = Project(
        name=data["name"],
        progress=data.get("progress", 0)
    )
    db.session.add(new_proj)
    db.session.commit()
    return jsonify({"message": "Project created", "project_id": new_proj.id}), 201

@app.route('/admin/projects/<int:project_id>', methods=['PUT'])
def admin_update_project_separate(project_id):
    p = Project.query.get_or_404(project_id)
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data"}), 400
    p.name = data.get("name", p.name)
    p.progress = data.get("progress", p.progress)
    db.session.commit()
    return jsonify({"message": "Project updated"}), 200

@app.route('/admin/projects/<int:project_id>', methods=['DELETE'])
def admin_delete_project_separate(project_id):
    p = Project.query.get_or_404(project_id)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"message": "Project deleted"}), 200

# --- 9. Admin Compliance Management (Policy) ---
@app.route('/admin/compliance/documents', methods=['GET'])
def admin_get_policy_documents():
    docs = PolicyDocument.query.order_by(PolicyDocument.created_at.desc()).all()
    data = [{
        "id": d.id,
        "title": d.title,
        "description": d.description,
        "status": d.status,
        "doc_url": d.doc_url,
        "created_at": d.created_at.isoformat()
    } for d in docs]
    return jsonify(data), 200

@app.route('/admin/compliance/documents/<int:doc_id>', methods=['GET'])
def admin_get_policy_document(doc_id):
    d = PolicyDocument.query.get_or_404(doc_id)
    return jsonify({
        "id": d.id,
        "title": d.title,
        "description": d.description,
        "status": d.status,
        "doc_url": d.doc_url,
        "created_at": d.created_at.isoformat()
    }), 200

@app.route('/admin/compliance/documents', methods=['POST'])
def admin_create_policy_document():
    data = request.get_json()
    if not data or "title" not in data:
        return jsonify({"message": "title is required"}), 400
    new_doc = PolicyDocument(
        title=data["title"],
        description=data.get("description", ""),
        status=data.get("status", "Active"),
        doc_url=data.get("doc_url", "")
    )
    db.session.add(new_doc)
    db.session.commit()
    return jsonify({"message": "Policy document created", "doc_id": new_doc.id}), 201

@app.route('/admin/compliance/documents/<int:doc_id>', methods=['PUT'])
def admin_update_policy_document(doc_id):
    d = PolicyDocument.query.get_or_404(doc_id)
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data"}), 400
    d.title = data.get("title", d.title)
    d.description = data.get("description", d.description)
    d.status = data.get("status", d.status)
    d.doc_url = data.get("doc_url", d.doc_url)
    db.session.commit()
    return jsonify({"message": "Policy document updated"}), 200

@app.route('/admin/compliance/documents/<int:doc_id>', methods=['DELETE'])
def admin_delete_policy_document(doc_id):
    d = PolicyDocument.query.get_or_404(doc_id)
    db.session.delete(d)
    db.session.commit()
    return jsonify({"message": "Policy document deleted"}), 200

@app.route('/admin/compliance/ack-history', methods=['GET'])
def admin_get_ack_history():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"message": "user_id query param is required"}), 400
    acks = db.session.query(PolicyAcknowledgement, PolicyDocument).join(
        PolicyDocument, PolicyAcknowledgement.policy_id == PolicyDocument.id
    ).filter(PolicyAcknowledgement.user_id == user_id).order_by(PolicyAcknowledgement.ack_date.desc()).all()
    data = []
    for ack, d in acks:
        data.append({
            "policy_id": d.id,
            "title": d.title,
            "ack_status": ack.ack_status,
            "ack_date": ack.ack_date.isoformat()
        })
    return jsonify(data), 200

# --- 10. Admin Chat Management (Already covered in public endpoints) ---
@app.route('/admin/chat/rooms', methods=['GET'])
def admin_get_chat_rooms():
    rooms = ChatRoom.query.all()
    data = [{"id": r.id, "name": r.name, "created_at": r.created_at.isoformat()} for r in rooms]
    return jsonify(data), 200

@app.route('/admin/chat/rooms/<int:room_id>', methods=['DELETE'])
def admin_delete_chat_room(room_id):
    r = ChatRoom.query.get_or_404(room_id)
    db.session.delete(r)
    db.session.commit()
    return jsonify({"message": "Chat room deleted"}), 200

# --- SOCKET.IO EVENTS FOR CHAT (Public) ---
@socketio.on('join')
def on_join(data):
    room_id = data.get("room_id")
    user_id = data.get("user_id")
    if room_id and user_id:
        join_room(str(room_id))
        print(f"User {user_id} joined room {room_id}")

@socketio.on('leave')
def on_leave(data):
    room_id = data.get("room_id")
    user_id = data.get("user_id")
    if room_id and user_id:
        leave_room(str(room_id))
        print(f"User {user_id} left room {room_id}")

@socketio.on('send_message')
def on_send_message(data):
    room_id = data.get("room_id")
    sender_id = data.get("sender_id")
    content = data.get("content")
    if not room_id or not sender_id or not content:
        return
    new_msg = ChatMessage(room_id=room_id, sender_id=sender_id, content=content)
    db.session.add(new_msg)
    db.session.commit()
    socketio.emit("new_message", {
        "id": new_msg.id,
        "room_id": new_msg.room_id,
        "sender_id": new_msg.sender_id,
        "content": new_msg.content,
        "timestamp": new_msg.timestamp.isoformat()
    }, room=str(room_id))

####################################################
# MAIN & TABLE CREATION
####################################################
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Tables created (if not already present).")
    socketio.run(app, debug=True, port=5000)
