#!/home/pi/venvs/photobox/bin/python
import flask
import networking

app = flask.Flask(__name__, template_folder="www/templateFiles", static_folder="www/staticFiles")

@app.route("/")
def index():
    navs = [
        {
            "title"     :   "Befehle",
            "target"    :   "commands" 
        }
    ]
    return flask.render_template("navigation_rows.html", navs=navs)

@app.route("/commands")
def commands():
    commands = [
        {
            "title"     : "Husch!",
            "subtitle"  : "Schalte die Slideshow um.",
            "cmd"       : "toggle"
        },
        {
            "title"     : "Snap!",
            "subtitle"  : "Schieße ein Photo.",
            "cmd"       : "shutter"
        },
    ]
    return flask.render_template("command_tiles.html", commands = commands, ret="index")

@app.route("/toggle")
def toggle():
    networking.command("TOGGLESCREEN")
    return ""


if(__name__ == "__main__"):
    app.run(debug = True, host="0.0.0.0", port=80)