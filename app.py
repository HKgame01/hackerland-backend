from cors import crossdomain
from replit import db
from hedera import *
from flask import *
import subprocess
import uuid
import json
import copy

class db_raw_base(object):
  def __getitem__(self, item):
    return json.loads(db.get_raw(item))

app = Flask(__name__, template_folder="", static_folder="")
db_raw = db_raw_base()

def uploadToHedera(bytes):
  transaction = FileCreateTransaction().setKeys(OPERATOR_KEY.getPublicKey()).setContents(bytes).setMaxTransactionFee(Hbar(2))
  file_id = transaction.execute(client).getReceipt(client).fileId.toString()
  return "https://song-store.epiccodewizard2.repl.co/" + file_id + ".mp3"

def getFirst10Seconds(bytes):
  proc = subprocess.Popen(["ffmpeg", "-i", "pipe:", "-ss", "00:00:00.0", "-t", "10", "-f", "mp3", "pipe:", "-y", "-nostdin"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
  out = proc.communicate(input=bytes)[0]
  proc.wait()
  return out

def createUserIfNotExist(uid):
  if uid not in list(db_raw["users"].keys()):
    db["users"][uid] = {}
    db["users"][uid]["uid"] = uid
    db["users"][uid]["music"] = []
    db["users"][uid]["favorites"] = []
    db["users"][uid]["time"] = 0

@app.before_request
def create_user():
  try:
    createUserIfNotExist(request.json["uid"])
  except:
    try:
      createUserIfNotExist(request.form["uid"])
    except:
      try:
        createUserIfNotExist(request.args.get("uid"))
      except:
        pass

@crossdomain(origin="*")
@app.route("/__db")
def db_get():
  retdata = {}
  retdata["users"] = list(db_raw["users"].values())
  retdata["music"] = list(db_raw["music"].values())
  return jsonify(retdata)

@crossdomain(origin="*")
@app.route("/pay", methods=["POST"])
def pay():
  tempdata = request.json
  db["users"][tempdata["uid"]]["music"].append(db_raw["music"][tempdata["mid"]])
  return ""

@crossdomain(origin="*")
@app.route("/music/all")
def all_music():
  return jsonify(list(db_raw["music"].values()))

@crossdomain(origin="*")
@app.route("/music/add", methods=["POST"])
def add_music():
  tempdata = copy.deepcopy(request.form.to_dict())
  bytesdata = request.files["audio"].read()
  publicUrlPreview = uploadToHedera(getFirst10Seconds(bytesdata))
  tempdata["preview"] = publicUrlPreview
  publicUrlAudio = uploadToHedera(bytesdata)
  tempdata["audio"] = publicUrlAudio
  mid = str(uuid.uuid4())
  tempdata["mid"] = mid
  db["music"][mid] = tempdata
  return ""

@crossdomain(origin="*")
@app.route("/play", methods=["POST"])
def play():
  tempdata = request.json
  db["users"][tempdata["uid"]]["time"] += tempdata["duration"]
  return ""

@crossdomain(origin="*")
@app.route("/user", methods=["GET"])
def get_user():
  return jsonify(db_raw["users"][request.args.get("uid")])

@crossdomain(origin="*")
@app.route("/player", methods=["GET"])
def get_player():
  retdata = db_raw["users"][request.args.get("uid")]
  del retdata["time"]
  return jsonify(retdata)

@crossdomain(origin="*")
@app.route("/leaderboard", methods=["GET"])
def leaderboard():
  users = list(db_raw["users"].values())
  users.sort(key=lambda user: user["time"], reverse=True)
  findata = []
  for user in users:
    humantime = ""
    if (user["time"] // 3600) != 0:
      humantime += str(user["time"] // 3600) + ":"
    if ((user["time"] % 3600) // 60) != 0:
      humantime += str((user["time"] % 3600) // 60) + ":"
    if ((user["time"] % 3600) % 60) != 0:
      humantime += str((user["time"] % 3600) % 60)
    findata.append({"uid": user["uid"], "time": humantime})
  return jsonify(findata)

@crossdomain(origin="*")
@app.route("/favorite", methods=["POST"])
def favorite():
  tempdata = request.json
  db["users"][tempdata["uid"]]["favorites"].append(db_raw["music"][tempdata["mid"]])
  return ""

@crossdomain(origin="*")
@app.route("/favorites", methods=["GET"])
def favorites():
  return jsonify(db_raw["users"][request.args.get("uid")]["favorites"])

@crossdomain(origin="*")
@app.route("/music/one", methods=["GET"])
def one_music():
  return jsonify(db_raw["music"][request.args.get("mid")])

@crossdomain(origin="*")
@app.route("/<file_id>", methods=["GET", "POST"])
def return_file(file):
  return FileContentsQuery().setFileId(FileId.fromString(file_id)).execute(client).toByteArray()

app.run(host="0.0.0.0")
