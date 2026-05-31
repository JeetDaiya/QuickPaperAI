import os
from dotenv import load_dotenv
import uvicorn
from server.app import app
load_dotenv()
os.makedirs("../outputs", exist_ok=True) 




@app.get("/")
def read_root():
    return {"Hello": "World"}




if __name__ == "__main__":
    # Pass the app as a string ("main:app") to safely support reload features
    uvicorn.run("server.main:app", host="127.0.0.1", port=8000, reload=True)
    