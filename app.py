"""
ScamShield - Flask application entry point.
Serves the frontend and exposes API routes.
"""

from flask import Flask, render_template, jsonify

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "ScamShield", "version": "0.1.0"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
