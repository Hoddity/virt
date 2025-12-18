from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from . import models, crud, database
from .utils import upload_image_to_yc

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/tasks")
def read_tasks(db: Session = Depends(get_db)):
    return crud.get_tasks(db)

@app.get("/tasks/{task_id}")
def read_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/tasks")
async def create_task_endpoint(
        title: str = Form(...),  # Используем Form() вместо просто параметров
        description: str = Form(None),
        image: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    image_url = None
    if image:
        image_url = upload_image_to_yc(image)

    task = crud.create_task(db, title, description, image_url)
    return task

@app.put("/tasks/{task_id}")
def update_task(task_id: int, title: str = None, description: str = None, status: str = None, db: Session = Depends(get_db)):
    task = crud.update_task(db, task_id, title, description, status)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.delete_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True}