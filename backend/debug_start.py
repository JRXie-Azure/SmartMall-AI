import sys, os, traceback

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'startup_log.txt')

with open(log_file, 'w', encoding='utf-8') as f:
    try:
        backend = os.path.dirname(os.path.abspath(__file__))
        f.write(f"CWD: {os.getcwd()}\n")
        f.write(f"Script dir: {backend}\n")
        sys.path.insert(0, backend)
        os.chdir(backend)
        f.write(f"New CWD: {os.getcwd()}\n")
        f.write("Importing app.main...\n")
        f.flush()

        from app.main import app
        f.write("Import OK!\n")
        f.flush()

        import uvicorn
        f.write("Importing uvicorn OK!\n")
        f.write("Starting server on port 8001...\n")
        f.flush()

        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
    except Exception as e:
        f.write(f"\nERROR: {e}\n")
        traceback.print_exc(file=f)
