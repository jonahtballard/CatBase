Here’s a **basic, clean `README.md`** you can drop in right now:

```markdown
# CatBase

CatBase is a University of Vermont (UVM) course search and exploration tool.  
It combines current and historical course data into a searchable database, with filters for semester, year, credits, and instructor.

## Features
- Search courses by subject, number, or title
- Filter by semester, year, credits, and instructor
- Live enrollment data for the current term
- Historical course data back to 1995

## Project Structure
```

backend/        # Flask backend and API
frontend/       # (Optional) React frontend
data/raw/       # Raw source data (not committed to Git)
data/processed/ # Cleaned/normalized data (not committed to Git)

````

## Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/jonahtballard/CatBase.git
cd CatBase
````

### 2. Set up the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Backend will run at: `http://localhost:5000`

### 3. (Optional) Set up the frontend

```bash
cd frontend
npm install
npm start
```

Frontend will run at: `http://localhost:3000`

## Data

Data files in `data/raw` and `data/processed` are ignored in Git.
Use the included scripts in `backend/scripts` to fetch and process data from UVM sources.

## License

MIT

```

---

Do you want me to make you **an even shorter 5-line README** for now,  
and then later we can expand it once CatBase is fully wired up? That’s a common early-stage pattern.
```
