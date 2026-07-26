import subprocess, sys, os, time

backend = r'C:\Users\谢键荣\SmartMall-AI\backend'
log_path = os.path.join(backend, 'uvicorn_output.log')

env = os.environ.copy()
env['PYTHONUNBUFFERED'] = '1'

with open(log_path, 'w', encoding='utf-8', buffering=1) as log:
    proc = subprocess.Popen(
        [sys.executable, '-u', '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8001'],
        cwd=backend,
        stdout=log,
        stderr=subprocess.STDOUT,
        env=env,
        creationflags=0x00000200  # CREATE_NEW_PROCESS_GROUP
    )
    print(f"Started PID: {proc.pid}")

# Monitor for 10 seconds to see if it crashes
for i in range(10):
    time.sleep(1)
    poll = proc.poll()
    if poll is not None:
        print(f"Process exited at second {i+1} with code: {poll}")
        with open(log_path, 'r', encoding='utf-8') as f:
            print("=== FULL LOG ===")
            print(f.read())
        break
else:
    print(f"Process {proc.pid} survived 10 seconds - still running!")
