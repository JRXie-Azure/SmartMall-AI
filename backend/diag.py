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
        f.write(f"Python: {sys.executable}\n")
        f.write(f"Python version: {sys.version}\n")
        f.flush()

        f.write("Step 1: Importing app.main...\n")
        f.flush()
        from app.main import app
        f.write(f"Step 1 OK: app = {app}\n")
        f.flush()

        f.write("Step 2: Importing uvicorn...\n")
        f.flush()
        import uvicorn
        f.write(f"Step 2 OK: uvicorn version = {uvicorn.__version__}\n")
        f.flush()

        f.write("Step 3: Testing uvicorn.Config...\n")
        f.flush()
        config = uvicorn.Config(app=app, host="0.0.0.0", port=8001, log_level="info")
        f.write(f"Step 3 OK: config created\n")
        f.flush()

        f.write("Step 4: Testing uvicorn.Server...\n")
        f.flush()
        server = uvicorn.Server(config=config)
        f.write(f"Step 4 OK: server created\n")
        f.flush()

        f.write("ALL CHECKS PASSED - ready to start\n")
    except Exception as e:
        f.write(f"\nERROR at some step: {e}\n")
        traceback.print_exc(file=f)
