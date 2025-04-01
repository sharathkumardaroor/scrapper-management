from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Form, UploadFile, File, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
import cloudscraper
import re
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database Setup
DATABASE_URL = "sqlite:///./scraper.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Webpage(Base):
    __tablename__ = "webpages"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    raw_html = Column(Text, nullable=True)
    status = Column(String, default="pending")
    status_code = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# FastAPI Application
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Pydantic Models
class TaskInput(BaseModel):
    url: str

class TaskOut(BaseModel):
    id: int
    url: str
    raw_html: Optional[str] = None
    status: Optional[str] = "pending"
    status_code: Optional[int] = None
    created_at: datetime
    class Config:
        orm_mode = True

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Background Task
def run_scraper_db(task_id: int):
    db = SessionLocal()
    try:
        task = db.query(Webpage).filter(Webpage.id == task_id).first()
        if not task:
            print(f"Task {task_id} not found")
            return
        
        print(f"Starting scraping: {task.url}")
        task.status = "running"
        db.commit()
        
        try:
            scraper = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows"})
            response = scraper.get(task.url)
            task.raw_html = response.text
            task.status = "completed"
            task.status_code = response.status_code
        except Exception as e:
            print(f"Error scraping {task.url}: {e}")
            task.status = "failed"
        
        db.commit()
    finally:
        db.close()

# API Endpoints
@app.get("/api/tasks", response_model=List[TaskOut])
def list_tasks_api(db: Session = Depends(get_db)):
    return db.query(Webpage).all()

@app.post("/api/tasks", response_model=TaskOut)
def create_task_api(task_in: TaskInput, db: Session = Depends(get_db)):
    existing = db.query(Webpage).filter(Webpage.url == task_in.url).first()
    if existing:
        raise HTTPException(status_code=400, detail="URL already exists")
    
    task = Webpage(url=task_in.url)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

# UI Endpoints
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/create-tasks")
async def create_tasks(
    request: Request,
    background_tasks: BackgroundTasks,
    url: Optional[str] = Form(None),
    bulk_file: Optional[UploadFile] = File(None),
    bulk_urls: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    urls = []
    
    # Process single URL
    if url and url.startswith("http"):
        urls.append(url.strip())
    
    # Process bulk file
    if bulk_file:
        try:
            content = await bulk_file.read()
            text = content.decode().strip()
            urls += [u.strip() for u in re.split(r'[\n,]', text) if u.strip().startswith("http")]
        except Exception as e:
            return handle_error(request, db, f"File error: {str(e)}")
    
    # Process bulk URLs textarea
    if bulk_urls:
        urls += [u.strip() for u in bulk_urls.split(',') if u.strip().startswith("http")]
    
    # Deduplicate
    urls = list(set(urls))
    
    if not urls:
        return handle_error(request, db, "No valid URLs provided")
    
    # Create tasks
    new_count = 0
    for url in urls:
        existing = db.query(Webpage).filter(Webpage.url == url).first()
        if not existing:
            task = Webpage(url=url)
            db.add(task)
            db.commit()
            db.refresh(task)
            background_tasks.add_task(run_scraper_db, task.id)
            new_count += 1
    
    if new_count == 0:
        return handle_error(request, db, "All URLs already exist in the system")
    
    return RedirectResponse(url="/", status_code=303)

def handle_error(request: Request, db: Session, error: str):
    tasks = db.query(Webpage).all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "tasks": tasks,
        "error": error
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", reload=True)