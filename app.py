from core import app
import uvicorn

app = app

if __name__ == "__main__":
    uvicorn.run("core:app", host="0.0.0.0", port=8000, reload=True)
