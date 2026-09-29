import os
import sys

# Ensure datetime is imported for main.py
content = open(r"C:\Users\jalde\python\firstporgram.py\metrotest76\backend\main.py", "r").read()
if "from datetime import datetime" not in content:
    content = "from datetime import datetime\n" + content
    open(r"C:\Users\jalde\python\firstporgram.py\metrotest76\backend\main.py", "w").write(content)
