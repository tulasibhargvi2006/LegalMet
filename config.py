import os

UPLOAD_FOLDER = 'static/uploads'
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
# MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

# # Mandatory declarations as per Legal Metrology Rules
# MANDATORY_FIELDS = {
#     'manufacturer': 'Manufacturer / Packer / Importer',
#     'product_name': 'Product Name',
#     'net_quantity': 'Net Quantity',
#     'mrp': 'Maximum Retail Price (MRP)',
#     'mfg_date': 'Manufacturing Date',
#     'expiry_date': 'Expiry / Best Before',
#     'country_of_origin': 'Country of Origin (if imported)',
#     'consumer_care': 'Consumer Care Details',
#     'unit_sale_price': 'Unit Sale Price (if applicable)'
# }

# # Rules: each rule has a field, required flag, and severity if missing
# RULES = [
#     {'field': 'manufacturer', 'required': True, 'severity': 'High'},
#     {'field': 'product_name', 'required': True, 'severity': 'High'},
#     {'field': 'net_quantity', 'required': True, 'severity': 'High'},
#     {'field': 'mrp', 'required': True, 'severity': 'High'},
#     {'field': 'mfg_date', 'required': True, 'severity': 'High'},
#     {'field': 'expiry_date', 'required': True, 'severity': 'High'},
#     {'field': 'country_of_origin', 'required': False, 'severity': 'Low'},   # only for imports
#     {'field': 'consumer_care', 'required': True, 'severity': 'High'},
#     {'field': 'unit_sale_price', 'required': False, 'severity': 'Medium'},
# ]

MONGO_URI = "mongodb://localhost:27017/"   # change if using MongoDB Atlas
DB_NAME = "legalmet_db"
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
SECRET_KEY = 'your-super-secret-key-change-this'