# ECHS login credentials - yahi folder ki credentials.txt se padhta hai (ek hi jagah rakho).
# credentials.txt format:  USERNAME=...   PASSWORD=...
import os

USERNAME = ""
PASSWORD = ""

_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.txt")
if os.path.exists(_f):
    for line in open(_f, encoding="utf-8"):
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip().upper(), val.strip()
        if key == "USERNAME":
            USERNAME = val
        elif key == "PASSWORD":
            PASSWORD = val
