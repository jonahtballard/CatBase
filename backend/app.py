from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes and origins

@app.route("/")
def index():
    return "Hello, world!"

if __name__ == "__main__":
    app.run(debug=True)
