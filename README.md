# 🚗 Vehicle Parking Management System

A web-based Parking Management System built using **Python Flask**. This application enables users to register/login, park or remove vehicles, and track vehicle activity. Admins have access to dashboards for managing users and viewing summaries.

![App Screenshot](./Parking%20App.png)

---

## 🔧 Features

* 👤 User registration and login
* 🅿️ Add or remove parked vehicles
* 📊 View parking history
* 👮 Admin panel for user management
* 💾 SQLite database for data persistence
* 🎨 Clean and responsive UI with HTML templates (Jinja2)

---

## 📁 Project Structure

```
vehicle-parking-management-system/
├── parkingManagement/
│   ├── __init__.py           # App and DB config
│   ├── controllers.py        # Route handlers
│   ├── forms.py              # Flask-WTF forms
│   ├── modals.py             # SQLAlchemy models
│   └── templates/            # HTML templates
├── run.py                    # App entry point
├── requirements.txt          # Python dependencies
├── .flaskenv                 # Flask environment vars
├── Parking App.png           # Screenshot
└── README.md
```

---

## 🚀 Getting Started

### ✅ Prerequisites

* Python 3.8 or higher
* `pip` package manager
* Virtual environment (optional but recommended)

### 📦 Installation

```bash
# Clone the repository
git clone https://github.com/kunal-bmd/Parking-Management-System.git
cd vehicle-parking-management-system

# (Optional) Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## ▶️ Running the App

```bash
# Start the Flask application
python run.py
```

Then visit: **[http://127.0.0.1:5000/](http://127.0.0.1:5000/)** in your browser.

---

## 🔐 Roles

**Users can:**

* Register and log in
* Park/remove vehicles
* View their parking history

**Admins can:**

* View all users and their parking summaries
* Access the admin dashboard

---

## 📌 Environment Config

`.flaskenv` file:

```
FLASK_APP=run.py
FLASK_ENV=development
```

---

## 📈 Future Improvements

* [ ] Add vehicle image upload with number plate detection
* [ ] Real-time parking availability view
* [ ] Role-based permissions with Flask-Login
* [ ] Export reports to CSV/PDF

---

## 🧾 License

This project is licensed under the MIT License.

---

**Developed with ❤️ by [Kunal BMD](https://github.com/kunal-bmd)**

