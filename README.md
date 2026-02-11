📦 StockWise – Flask Inventory Management System

StockWise is a simple, powerful inventory 
and sales analytics web application built 
with Flask. It helps businesses track 
stock, monitor sales trends, and 
identify top-performing products in real 
time.


 Live Demo

URL: https://13.61.26.20
The app uses a self-signed SSL 
certificate, so your browser will show 
a security warning.
Click Advanced → Proceed to access the 
site safely.


Features
	Sales trend analytics dashboard
	Inventory management (Add / Take / Track stock)
	Fast-selling product detection
  Top money-making product insights
  Stock history tracking
	Printable stock sheets
	Stock health monitoring (Out-of-stock alerts)
	HTTPS enabled (Self-signed SSL)
	Deployed on AWS Linux cloud server


Tech Stack
	•	Backend: Flask (Python)
	•	Frontend: HTML, CSS, JavaScript, Bootstrap
	•	Database: SQLite (can be switched to PostgreSQL/MySQL)
	•	Charts: Chart.js
	•	Server: AWS EC2 (Linux)
	•	Security: Self-signed SSL certificate

Screenshorts

Demo screenshorts are included above
in the root directory of the project.

Installation 

# Clone repository
git clone https://github.com/your-username/Flask-inventory-app.git

# Enter project folder
cd Flask-inventory-app

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate   # Linux / Mac
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

Deployment (AWS Linux)

The app is hosted on an AWS Linux cloud machine:

Server IP: 13.61.26.20
Protocol: HTTPS
SSL: Self-signed certificate

SSL Notice

This project uses a self-signed SSL certificate for HTTPS encryption. Browsers may show:

“Your connection is not private”

This is expected. You can safely proceed for development/testing.

For production, use Let’s Encrypt or a trusted CA.


Key Modules
	•	app.py – Main Flask application
	•	inventory/ – Stock logic
	•	analytics/ – Sales & performance insights
	•	templates/ – HTML views
	•	static/ – CSS, JS, charts
	•	database.db – SQLite database


Use Cases
	•	Small retail shops
	•	Convenience stores
	•	Mini supermarkets
	•	Inventory tracking projects
	•	Business analytics learning


Future Improvements
	•	User authentication / roles
	•	REST API
	•	Barcode scanning
	•	Supplier management
	•	Automatic reorder alerts
	•	Cloud database (PostgreSQL)
	•	Real SSL certificate
	•	Mobile responsive optimization











  





