import subprocess, sys
r = subprocess.run(
    [sys.executable, r"src\features\build_data_log.py"],
    capture_output=True, text=True,
    cwd=r"c:\Users\userp\Desktop\ShalaScope_Maharashtra"
)
print("STDOUT:", r.stdout)
print("STDERR:", r.stderr[:500] if r.stderr else "")
print("RC:", r.returncode)
