import os
import hashlib
from flask import Flask, request, render_template, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pymongo
from config import MONGO_URI, DB_NAME, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH, SECRET_KEY
from utils.ocr_engine import OCREngine
from utils.rule_engine import RuleEngine
from utils.image_processor import analyze_text_placement

from bson.objectid import ObjectId

# inside upload_file() after OCR processing


app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# MongoDB connection
client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
users_col = db['users']
rules_col = db['rules']
scans_col = db['scans']

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ocr = OCREngine()
rule_engine = RuleEngine()

# ---------- Helper functions ----------
def get_rules_from_db():
    """Return list of active rules from MongoDB."""
    return list(rules_col.find({'active': True}, {'_id': 0}))

def get_user_by_phone(phone):
    return users_col.find_one({'phone': phone})

def create_user(full_name, phone, password, role='user'):
    hashed = generate_password_hash(password)
    users_col.insert_one({
        'full_name': full_name,
        'phone': phone,
        'password': hashed,
        'role': role,
        'created_at': datetime.utcnow()
    })

def seed_default_rules():
    if rules_col.count_documents({}) == 0:
        default_rules = [
            {'field': 'manufacturer', 'label': 'Manufacturer / Packer / Importer', 'required': True, 'severity': 'High', 'active': True},
            {'field': 'product_name', 'label': 'Product Name', 'required': True, 'severity': 'High', 'active': True},
            {'field': 'net_quantity', 'label': 'Net Quantity', 'required': True, 'severity': 'High', 'active': True},
            {'field': 'mrp', 'label': 'Maximum Retail Price (MRP)', 'required': True, 'severity': 'High', 'active': True},
            {'field': 'mfg_date', 'label': 'Manufacturing Date', 'required': True, 'severity': 'High', 'active': True},
            {'field': 'expiry_date', 'label': 'Expiry / Best Before', 'required': True, 'severity': 'High', 'active': True},
            {'field': 'country_of_origin', 'label': 'Country of Origin (if imported)', 'required': False, 'severity': 'Low', 'active': True},
            {'field': 'consumer_care', 'label': 'Consumer Care Details', 'required': True, 'severity': 'High', 'active': True},
            {'field': 'unit_sale_price', 'label': 'Unit Sale Price (if applicable)', 'required': False, 'severity': 'Medium', 'active': True}
        ]
        rules_col.insert_many(default_rules)

# ---------- Authentication routes ----------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        user = get_user_by_phone(phone)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))
        flash('Invalid phone or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        password = request.form.get('password')
        if get_user_by_phone(phone):
            flash('Phone number already registered')
            return redirect(url_for('register'))
        create_user(full_name, phone, password)
        flash('Registration successful. Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------- User home (upload) ----------
@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')

# ---------- Upload and process ----------

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('home'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('home'))
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
        flash('Invalid file type')
        return redirect(url_for('home'))

    filename = secure_filename(file.filename)
    # 1. Save to static/uploads/ (full filesystem path)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # 2. Store a clean relative path (for url_for) – no 'static/' prefix, forward slashes
    relative_path = os.path.join('uploads', filename).replace('\\', '/')

    # 3. OCR processing
    extracted_text = ocr.extract_text(filepath)
    extracted_fields = ocr.extract_fields(extracted_text)
    rules = get_rules_from_db()
    validation_result = rule_engine.validate(extracted_fields, rules)
    placement_info = analyze_text_placement(filepath)

    # 4. Save scan to database with relative_path
    scans_col.insert_one({
        'user_id': ObjectId(session['user_id']),   # ✅ convert to ObjectId
    'image_path': relative_path,
    'extracted_fields': extracted_fields,
    'extracted_text': extracted_text,           # ✅ save raw text
    'violations': validation_result['violations'],
    'status': validation_result['status'],
    'timestamp': datetime.utcnow()
    })
    
    return render_template('result.html',
                           image_path=filepath,   # full path used in <img src="{{ image_path }}"> (works because result.html serves it directly)
                           extracted_text=extracted_text,
                           extracted_fields=extracted_fields,
                           validation=validation_result,
                           placement=placement_info)

# ---------- Admin routes ----------
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access only')
        return redirect(url_for('login'))
    rules = list(rules_col.find({}, {'_id': 0}))
    total_users = users_col.count_documents({})
    total_scans = scans_col.count_documents({})
    compliant_scans = scans_col.count_documents({'status': 'COMPLIANT'})
    noncompliant_scans = scans_col.count_documents({'status': 'NON-COMPLIANT'})
    return render_template('admin.html',
                           rules=rules,
                           total_users=total_users,
                           total_scans=total_scans,
                           compliant_scans=compliant_scans,
                           noncompliant_scans=noncompliant_scans)

@app.route('/admin/rules/add', methods=['GET', 'POST'])
def admin_add_rule():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access only')
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_rule = {
            'field': request.form.get('field'),
            'label': request.form.get('label'),
            'required': request.form.get('required') == 'on',
            'severity': request.form.get('severity'),
            'active': request.form.get('active') == 'on'
        }
        rules_col.insert_one(new_rule)
        flash('Rule added')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_edit.html', rule=None)

@app.route('/admin/rules/edit/<field>', methods=['GET', 'POST'])
def admin_edit_rule(field):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access only')
        return redirect(url_for('login'))
    rule = rules_col.find_one({'field': field})
    if not rule:
        flash('Rule not found')
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        updated = {
            'label': request.form.get('label'),
            'required': request.form.get('required') == 'on',
            'severity': request.form.get('severity'),
            'active': request.form.get('active') == 'on'
        }
        rules_col.update_one({'field': field}, {'$set': updated})
        flash('Rule updated')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_edit.html', rule=rule)

# ---------- Admin: Users ----------
@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access only')
        return redirect(url_for('login'))
    users = list(users_col.find({}, {'password': 0}))  # exclude password
    return render_template('admin_users.html', users=users)


@app.route('/admin/reports')
def admin_reports():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access only')
        return redirect(url_for('login'))

    status_filter = request.args.get('status', '').upper()
    query = {}
    if status_filter in ['COMPLIANT', 'NON-COMPLIANT']:
        query['status'] = {'$regex': f'^{status_filter}$', '$options': 'i'}  # case-insensitive

    pipeline = [
        {'$match': query},
        {'$lookup': {
            'from': 'users',
            'localField': 'user_id',
            'foreignField': '_id',
            'as': 'user'
        }},
        {'$unwind': {'path': '$user', 'preserveNullAndEmptyArrays': True}},
        {'$project': {
            '_id': 1,
            'image_path': 1,
            'extracted_fields': 1,
            'violations': 1,
            'status': 1,
            'timestamp': 1,
            'extracted_text': 1,
            'user_full_name': '$user.full_name',
            'user_phone': '$user.phone'
        }},
        {'$sort': {'timestamp': -1}}
    ]
    scans = list(scans_col.aggregate(pipeline))
    for s in scans:
        s['_id'] = str(s['_id'])

    return render_template('admin_reports.html', scans=scans, status_filter=status_filter)
# ---------- Admin: Report detail (optional) ----------
@app.route('/admin/report/<scan_id>')
def admin_report_detail(scan_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access only')
        return redirect(url_for('login'))
    from bson.objectid import ObjectId

    pipeline = [
        {'$match': {'_id': ObjectId(scan_id)}},
        {'$lookup': {
            'from': 'users',
            'localField': 'user_id',
            'foreignField': '_id',
            'as': 'user'
        }},
        {'$unwind': {'path': '$user', 'preserveNullAndEmptyArrays': True}}
    ]
    results = list(scans_col.aggregate(pipeline))
    if not results:
        flash('Scan not found')
        return redirect(url_for('admin_reports'))

    scan = results[0]
    scan['_id'] = str(scan['_id'])
    if scan.get('user'):
        scan['user']['_id'] = str(scan['user']['_id'])

    return render_template('admin_report_detail.html', scan=scan)

@app.route('/admin/rules/delete/<field>')
def admin_delete_rule(field):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access only')
        return redirect(url_for('login'))
    rules_col.delete_one({'field': field})
    flash('Rule deleted')
    return redirect(url_for('admin_dashboard'))

# ---------- Seed default admin user ----------
def seed_admin():
    if not users_col.find_one({'role': 'admin'}):
        # Create admin with phone: 9999999999, password: admin123
        create_user('Admin', '9999999999', 'admin123', role='admin')

# ---------- Run ----------
if __name__ == '__main__':
    seed_default_rules()
    seed_admin()
    app.run(debug=True)

