#!/home/pi/venvs/photobox/bin/python
import flask
import networking
import housekeeping

app = flask.Flask(__name__, template_folder="www/templateFiles", static_folder="www/staticFiles")

@app.route("/")
def index():
    navs = [
        {
            "title"     :   "Befehle",
            "target"    :   "commands" 
        },{
            "title"     :   "Prozesse",
            "target"    :   "procs" 
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
        {
            "title"     : "Bye!",
            "subtitle"  : "Fährt das System herunter.",
            "cmd"       : "shutdown"
        }
    ]
    return flask.render_template("command_tiles.html", commands = commands, ret="index")

@app.route("/procs")
def procs():
    state_colors = {
        "FATAL"         : "red",
        "RUNNING"       : "green",
        "RESTARTING"    : "orange"
    }
    procs = housekeeping.supervisor_get_process_info()
    elems = []
    for proc in procs:
        elems.append({
            "name"      :   proc["name"],
            "state"     :   proc["statename"],
            "color"     :   state_colors.get(proc["statename"], "black"),
            "route"     :   "proc_info",
        })
    return flask.render_template("process_rows.html", elems=elems, ret="index")

@app.route("/proc_info/<proc>")
def proc_info(proc = None):
    state_colors = {
        "FATAL"         : "red",
        "RUNNING"       : "green",
        "RESTARTING"    : "orange"
    }
    procs = housekeeping.supervisor_get_process_info(proc)
    elems = [{
            "name"      :   "Test",
            "state"     :   "Test",
            "color"     :   "red",
            "route"     :   "index"
        }]

    return flask.render_template("process_infos.html", elems=elems, ret="index")

@app.route("/toggle")
def toggle():
    networking.command("TOGGLESCREEN")
    return ""

@app.route("/shutdown")
def shutdown():
    networking.command("SHUTDOWN")
    return ""


if(__name__ == "__main__"):
    app.run(debug = True, host="0.0.0.0", port=80)