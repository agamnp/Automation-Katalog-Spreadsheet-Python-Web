# backend/main.py
import os
import importlib.util
import inspect
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

MODULE_FOLDER = "Module"

app = FastAPI(title="Automasi Google Sheet Backend")

# Setup CORS supaya frontend Next.js bisa akses tanpa masalah
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # sesuaikan dengan alamat frontend
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunRequest(BaseModel):
    name: str

def load_functions():
    functions = {}
    for filename in os.listdir(MODULE_FOLDER):
        if filename.endswith(".py") and not filename.startswith("_"):
            filepath = os.path.join(MODULE_FOLDER, filename)
            module_name = filename[:-3]

            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                print(f"Gagal load module {module_name}: {e}")
                continue

            for name, func in inspect.getmembers(module, inspect.isfunction):
                if name.startswith("main_"):
                    functions[name] = func
    return functions

@app.get("/functions")
def get_functions():
    funcs = load_functions()
    return {"functions": list(funcs.keys())}

@app.post("/run")
def run_function(req: RunRequest):
    funcs = load_functions()
    func = funcs.get(req.name)
    if not func:
        raise HTTPException(status_code=404, detail="Function not found")

    output = []
    def logger(msg):
        output.append(str(msg))

    try:
        func(logger=logger)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "success", "output": output}
