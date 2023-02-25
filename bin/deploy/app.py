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
    title = "...."
    sections = [{
        "sectiontype"   : "rows",
        "elems"         : [{
            "href"  : flask.url_for("commands"),
            "labels": [{
                "text" : "Befehle",
                "class": "title rowLeft",
                "style": ""
            },{
                "text" : ">",
                "class": "info rowRight"
            }]
        },{
            "href"  : flask.url_for("procs"),
            "labels": [{
                "text" : "Prozesse",
                "class": "title rowLeft",
                "style": ""
            },{
                "text" : ">",
                "class": "info rowRight",
                "style": ""
            }]
        }]
    }]
    return flask.render_template("standard_page.html", sections=sections, title=title)

@app.route("/commands")
def commands():
    title = "Befehle"
    sections = [{
        "sectiontype"   : "tiles",
        "elems"         : [{
            "onclick"   : f"Exec('toggle')",
            "title"     : "Husch!",
            "subtitle"  : "Schalte die Slideshow um."
        },{
            "onclick"   : f"Exec('shutter')",
            "title"     : "Snap!",
            "subtitle"  : "Schieße ein Photo."
        },{
            "onclick"   : f"Exec('countdown')",
            "title"     : "3..2..1..",
            "subtitle"  : "Starte den Countdown."
        },{
            "onclick"   : f"Exec('shutdown')",
            "title"     : "Bye!",
            "subtitle"  : "Fahre das System herunter."
        }]
    }]

    return flask.render_template("standard_page.html", sections=sections, title=title, ret="index")

@app.route("/procs")
def procs():
    title = "Prozesse"
    procs = secretary.supervisor_get_process_info()
    elems = []
    for proc in procs:
        elems.append({
            "href"  : flask.url_for("proc_info", proc=proc["name"]),
            "labels": [{
                "text" : proc["name"],
                "class": "title rowLeft",
                "style": ""
            },{
                "text" : proc["statename"],
                "class": "info rowRight",
                "style": "color : " + STATE_COLORS.get(proc["statename"], "black")
            }]
        })
    sections = [{
        "sectiontype"   : "rows",
        "elems"         : elems
    }]

    return flask.render_template("standard_page.html", sections=sections, title=title, ret="index")

@app.route("/proc_info/<proc>")
def proc_info(proc):
    procname = proc
    proc = secretary.supervisor_get_process_info(proc)
    uptime = ""
    startttile = "An!"
    startsubtitle = "Starte das Programm."
    bRunning = False
    if(proc["state"] == 20):
        bRunning = True
        uptime = tools.seconds2hms(proc["now"] - proc["start"])
        startttile = "Mach Neu!"
        startsubtitle = "Starte das Programm erneut."
    sections = [{
        "sectiontype"   : "rows",
        "elems"         : [{
            "href"  : "",
            "labels": [{
                "text" : "Status",
                "class": "info rowLeft",
                "style": ""
            },{
                "text" : proc["statename"],
                "class": "info rowRight",
                "style": "color : " + STATE_COLORS.get(proc["statename"], "black")
            }]
        },{
            "href"  : "",
            "labels": [{
                "text" : "Uptime",
                "class": "info rowLeft",
                "style": ""
            },{
                "text" : uptime,
                "class": "info rowRight"
            }]
        },{
            "href"  : flask.url_for("proc_log", proc=procname),
            "labels": [{
                "text" : "Log",
                "class": "info rowLeft",
                "style": ""
            },{
                "text" : ">",
                "class": "info rowRight"
            }]
        }]
    },{
        "sectiontype"   : "tiles",
        "elems"         : [{
            "onclick"   : f"Exec_Proc('{procname}', 'start')",
            "title"     : startttile,
            "subtitle"  : startsubtitle
        },{
            "onclick"   : f"Exec_Proc('{procname}', 'stop')" if bRunning else "",
            "title"     : "Aus!",
            "subtitle"  : "Beende das Programm.",
            "style"     : "opacity : 1;" if bRunning else "opacity : 0.3;"
        }]
    }]

    return flask.render_template("standard_page.html", sections=sections, title=procname, ret="procs")

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