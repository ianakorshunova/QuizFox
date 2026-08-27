import os
import runpy

os.environ["QUIZFOX_APP_MODE"] = "owner"

runpy.run_path("app.py")