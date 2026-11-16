import os
import tempfile

# Use a throwaway in-memory database and upload folder for every test run. This must
# be set before the app modules are imported, because settings and the database
# engine are created at import time.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="adguard-test-uploads-")
