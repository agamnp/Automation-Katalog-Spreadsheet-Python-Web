import os
import importlib.util
import inspect
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import time

MODULE_FOLDER = "Module"

app = FastAPI(title="Automasi Google Sheet Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # ganti ke domain frontend jika perlu
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

def load_functions():
    functions = {}
    for filename in os.listdir(MODULE_FOLDER):
        if filename.endswith(".py") and not filename.startswith("_"):
            path = os.path.join(MODULE_FOLDER, filename)
            spec = importlib.util.spec_from_file_location(filename[:-3], path)
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                print(f"Gagal load module {filename}: {e}")
                continue

            for name, fn in inspect.getmembers(module, inspect.isfunction):
                if name.startswith("main_"):
                    functions[name] = fn
    return functions

@app.get("/functions")
def get_functions():
    funcs = load_functions()
    return {"functions": list(funcs.keys())}

@app.get("/stream/{name}")
def stream_function(name: str):
    funcs = load_functions()
    func = funcs.get(name)
    if not func:
        raise HTTPException(status_code=404, detail="Function not found")

    def event_generator():
        # Generator jadi logger yang langsung yield tiap pesan
        def logger(msg):
            yield f"data: {msg}\n\n"

        # Butuh trik supaya bisa yield dari fungsi logger yang dipanggil dalam func
        # Gunakan queue / iterator untuk "meneruskan" pesan logger ke event_generator
        from queue import Queue, Empty
        import threading

        q = Queue()

        def thread_logger(msg):
            q.put(str(msg))

        # Jalankan fungsi di thread supaya bisa baca log realtime dari queue
        def target():
            try:
                func(logger=thread_logger)
            except Exception as e:
                q.put(f"❌ Terjadi error saat proses utama: {e}")
            q.put(None)  # tanda selesai

        thread = threading.Thread(target=target)
        thread.start()

        while True:
            try:
                msg = q.get(timeout=0.1)
                if msg is None:
                    break
                yield f"data: {msg}\n\n"
            except Empty:
                # Kalau queue kosong, terus tunggu
                continue

        yield "event: end\ndata: ✅ Proses selesai\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}

@app.post("/run")
def run_function(req: dict):
    funcs = load_functions()
    func = funcs.get(req.get("name"))
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
