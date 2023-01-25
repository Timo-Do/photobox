#!/home/pi/venvs/photobox/bin/python
import flask
import networking

app = flask.Flask(__name__, template_folder="www/templateFiles", static_folder="www/staticFiles")

@app.route("/")
def index():
    return flask.render_template("index.html")

@app.route("/toggle")
def toggle():
    networking.command("TOGGLESCREEN")
    return ""

if(__name__ == "__main__"):
    app.run(debug = True, host="0.0.0.0", port=80)