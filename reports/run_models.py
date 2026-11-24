import subprocess, sys, os
env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
r = subprocess.run(
    [sys.executable, r"src\models\run_prediction_modules.py"],
    capture_output=True, text=True, encoding="utf-8",
    cwd=r"c:\Users\userp\Desktop\ShalaScope_Maharashtra",
    env=env,
)
print(r.stdout[-5000:] if len(r.stdout) > 5000 else r.stdout)
if r.stderr:
    print("STDERR:", r.stderr[-1500:])
print("RC:", r.returncode)
