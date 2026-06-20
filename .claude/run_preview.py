"""Dev launcher for Claude preview — forces debug mode so SECRET_KEY isn't
required, then serves the existing Flask app on port 5000."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

os.environ.setdefault("FLASK_DEBUG", "1")
os.environ.setdefault("SECRET_KEY", "dev-preview-secret-key")
os.environ.setdefault("PORT", "5000")

from app import app  # noqa: E402  (env must be set before import)

# Hot-reload templates on edit without enabling the full debug reloader.
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
