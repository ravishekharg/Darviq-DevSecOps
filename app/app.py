from flask import Flask, jsonify, request
import os
import socket
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "service": "devsecops-demo",
        "status":  "healthy",
        "hostname": socket.gethostname(),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "version": os.getenv("APP_VERSION", "1.0.0")
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/ready")
def ready():
    return jsonify({"status": "ready"}), 200

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not found"}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({"error": "internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)