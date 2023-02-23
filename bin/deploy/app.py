#!/home/pi/venvs/photobox/bin/python
import flask
import ipc
import secretary
import datetime
from assets import tools

messenger = ipc.Messenger()
app = flask.Flask(__name__, template_folder="www/templateFiles", static_folder="www/staticFiles")

STATE_COLORS = {
    "FATAL"         : "red",
    "RUNNING"       : "green",
    "RESTARTING"    : "orange"
}

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
            "subtitle"  : "Fahre das System herunter.",
            "cmd"       : "shutdown"
        }
    ]
    return flask.render_template("command_tiles.html", commands = commands, ret="index")

@app.route("/procs")
def procs():

    procs = secretary.supervisor_get_process_info()
    elems = []
    for proc in procs:
        elems.append({
            "name"      :   proc["name"],
            "state"     :   proc["statename"],
            "color"     :   STATE_COLORS.get(proc["statename"], "black"),
            "route"     :   "proc_info",
        })
    return flask.render_template("process_rows.html", elems=elems, ret="index")

@app.route("/proc_info/<proc>")
def proc_info(proc):
    procname = proc
    proc = secretary.supervisor_get_process_info(proc)
    uptime = ""
    startname = "An!"
    startsubtitle = "Starte das Programm."
    terminate = ""
    if(proc["state"] == 20):
        uptime = tools.seconds2hms(proc["now"] - proc["start"])
        startname = "Mach Neu!"
        startsubtitle = "Starte das Programm erneut."
        terminate = "Aus!"
    proc_infos = {
        "name"          : procname,
        "state"         : proc["statename"],
        "statecolor"    : STATE_COLORS.get(proc["statename"], "black"),
        "uptime"        : uptime,
        "pid"           : proc["pid"],
        "startname"     : startname,
        "startsub"      : startsubtitle,
        "terminate"     : terminate
    }

    return flask.render_template("process_infos.html", proc_infos=proc_infos, ret="procs")

@app.route("/proc_log/<proc>")
def proc_log(proc):
    procname = proc
    log = secretary.supervisor_get_process_log(proc)

    return flask.render_template("process_log.html", procname=procname, log=log, ret="procs")

@app.route("/proc_cmd/<proc>/<cmd>")
def proc_cmd(proc, cmd):
    print(proc)
    print(cmd)
    return ""

@app.route("/toggle")
def toggle():
    messenger.publish("TOGGLESCREEN", "Website")
    return ""

@app.route("/shutdown")
def shutdown():
    messenger.publish("SHUTDOWN", "Website")
    return ""


if(__name__ == "__main__"):
    
    app.run(debug = True, host="0.0.0.0", port=80)