from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
import cloudscraper

from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# SQLite DB setup
DATABASE_URL = "sqlite:///./scraper.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}  # SQLite specific
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Webpage(Base):
    __tablename__ = "webpages"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    raw_html = Column(Text, nullable=True)
    status = Column(String, default="pending")
    status_code = Column(Integer, nullable=True)

# Create the database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI()

# Mount static files and setup templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Pydantic models for API input/output
class TaskInput(BaseModel):
    url: str

class TaskOut(BaseModel):
    id: int
    url: str
    raw_html: Optional[str] = None
    status: Optional[str] = "pending"
    status_code: Optional[int] = None

    class Config:
        orm_mode = True

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Background scraping function that creates its own DB session
def run_scraper_db(task_id: int):
    db = SessionLocal()
    try:
        task = db.query(Webpage).filter(Webpage.id == task_id).first()
        if not task:
            print(f"Task with id {task_id} not found")
            return
        print(f"Starting scraping for {task.url} (Task {task.id})...")
        try:
            # Create a cloudscraper instance with basic browser settings
            scraper = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows"})
            response = scraper.get(task.url)
            task.raw_html = response.text
            task.status = "completed"
            task.status_code = response.status_code
            print(f"Completed scraping for {task.url} (Task {task.id}), status_code: {response.status_code}")
        except Exception as e:
            print(f"Error scraping {task.url} (Task {task.id}): {e}")
            task.status = "failed"
        db.commit()
    finally:
        db.close()

# ----------------------
# API Endpoints
# ----------------------

@app.get("/api/tasks", response_model=List[TaskOut])
def list_tasks_api(db: Session = Depends(get_db)):
    """Return the list of scraper tasks as JSON."""
    tasks = db.query(Webpage).all()
    return tasks

@app.post("/api/tasks", response_model=TaskOut)
def create_task_api(task_in: TaskInput, db: Session = Depends(get_db)):
    """Create a new scraper task with an auto-generated ID."""
    existing = db.query(Webpage).filter(Webpage.url == task_in.url).first()
    if existing:
        raise HTTPException(status_code=400, detail="Task with this URL already exists")
    task = Webpage(url=task_in.url)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@app.post("/api/tasks/{task_id}/start")
def start_task_api(task_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger a scraper task as a background job."""
    task = db.query(Webpage).filter(Webpage.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Task already started or completed")
    task.status = "running"
    db.commit()
    background_tasks.add_task(run_scraper_db, task_id)
    return {"msg": f"Scraper task {task_id} started"}

# ----------------------
# UI Endpoints
# ----------------------

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, db: Session = Depends(get_db)):
    """Render the home page showing all tasks."""
    tasks = db.query(Webpage).all()
    return templates.TemplateResponse("index.html", {"request": request, "tasks": tasks, "error": None})

@app.post("/create-task")
def create_task_form(request: Request, url: str = Form(...), db: Session = Depends(get_db)):
    """Create a new task via the UI form."""
    existing = db.query(Webpage).filter(Webpage.url == url).first()
    if existing:
        error = "Task with this URL already exists."
        tasks = db.query(Webpage).all()
        return templates.TemplateResponse("index.html", {"request": request, "tasks": tasks, "error": error})
    task = Webpage(url=url)
    db.add(task)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/start-task/{task_id}")
def start_task_ui(request: Request, task_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Start a task via the UI button."""
    task = db.query(Webpage).filter(Webpage.id == task_id).first()
    if not task:
        error = "Task not found."
        tasks = db.query(Webpage).all()
        return templates.TemplateResponse("index.html", {"request": request, "tasks": tasks, "error": error})
    if task.status == "pending":
        task.status = "running"
        db.commit()
        background_tasks.add_task(run_scraper_db, task_id)
    return RedirectResponse(url="/", status_code=303)

# Run with: uvicorn app:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", reload=True)
