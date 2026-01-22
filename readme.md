## 🔧 Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python 3.8+** - [Download Python](https://python.org/downloads/)
- **pip** - Python package manager (comes with Python)
- **virtualenv** - For Python environment isolation
- **PostgreSQL** or **SQLite** - Database system
- **Git** - Version control system

### Verify Installation

```bash
python --version
pip --version
git --version
```

## 🚀 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/shauryasawai/Nest
cd Nest
```

### Step 2: Set Up Virtual Environment

Create and activate a virtual environment to isolate project dependencies:

#### Create Virtual Environment
```bash
python -m venv my_env
```

#### Install virtualenv (if not already installed)
```bash
pip install virtualenv
```

#### Activate Virtual Environment

**Windows:**
```bash
my_env\Scripts\activate
```

**macOS/Linux:**
```bash
source my_env/bin/activate
```

> 💡 **Note**: You should see `(my_env)` in your terminal prompt when the virtual environment is active.

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Database Setup

#### Apply Migrations
```bash
python manage.py migrate
```

#### Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### Step 5: Start the Development Server

```bash
python manage.py runserver
```

🎉 **Success!** Your application is now running at `http://127.0.0.1:8000/`
