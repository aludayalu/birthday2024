from flask import request, redirect
from monster import render, tokeniser, parser, Flask
import sys, json
import litedb, hashlib, time, random
import uuid, threading

users=litedb.get_conn("users")
teams=litedb.get_conn("teams")
wallets=litedb.get_conn("wallets")
prices=litedb.get_conn("prices")

starting_Price=500

current_Prices={"A":[starting_Price], "B":[starting_Price], "C":[starting_Price], "D":[starting_Price], "E":[starting_Price], "LTZ":[1]}

LTZ_Prices=prices.get("A")
if LTZ_Prices==None:
    for x in ["A", "B", "C", "D", "E"]:
        prices.set(x, [starting_Price])
else:
    for x in ["A", "B", "C", "D", "E"]:
        current_Prices[x]=prices.get(x)

def calculate_Prices():
    global current_Prices
    i=0
    assets_Trend={}
    while True:
        i+=1
        time.sleep(0.8)
        for asset in current_Prices:
            if asset=="LTZ":
                continue
            if asset not in assets_Trend:
                assets_Trend[asset]={"trend":5, "interval":10}
            asset_Prices=current_Prices[asset]
            if i%assets_Trend[asset]["interval"]==0:
                assets_Trend[asset]["trend"]=random.choice([0]*50+[1]*40+[2]*35+[3]*28+[4]*18+[5]*10+[6]*18+[7]*28+[8]*35+[9]*40+[10]*50)
                assets_Trend[asset]["interval"]=random.randrange(2, 20)
            new_Price=((random.random() * 10) - assets_Trend[asset]["trend"])+asset_Prices[-1]
            if new_Price<1:
                new_Price=starting_Price/10
            asset_Prices.append(new_Price)
            asset_Prices=asset_Prices[len(asset_Prices)-500:]
            prices.set(asset, asset_Prices)
            current_Prices[asset]=asset_Prices

def Wallet(id="", assets={}):
    return {"id":id, "assets":assets}

def Team(id="", name="", wallet="", people=[]):
    return {"id":id, "name":name, "wallet":wallet, "people":people}

def User(name="", username="", password="", team="", wallet=""):
    return {"name":name ,"username":username, "password":password, "team":team, "wallet":wallet}

app = Flask(__name__)

daisyui="<script>"+open("public/pako.js").read()+"</script>"+"""<script>
    function decompressGzippedString(base64String) {
        try {
            const binaryString = atob(base64String);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            const decompressedData = pako.inflate(bytes, { to: 'string' });
            return decompressedData;
        } catch (err) {
            console.error('An error occurred while decompressing the string:', err);
            return null;
        }
    }
    """+f"""
    var daisycss="{open("public/daisyui.b64").read()}";
    var style=document.createElement("style");
    style.textContent=decompressGzippedString(daisycss);
    document.head.appendChild(style);
    </script>
    """

tailwind="<script>"+open("public/tailwind.js").read()+"</script>"
footer=open("components/footer.html").read()

def auth():
    username=request.cookies.get("username")
    password=request.cookies.get("password")
    if username==None or password==None:
        return False
    user_Account=users.get(username)
    if user_Account==None:
        return False
    if user_Account["password"]==hashlib.sha256(password.encode()).hexdigest():
        return user_Account
    return False

@app.get("/")
def home():
    userAccount=auth()
    if not userAccount:
        return render("auth", locals()|globals())
    navbar=render("navbar", locals())
    card=render("card", locals())
    userAccount="<script>var userAccount="+json.dumps(userAccount)+"</script>"
    teams_List=[]
    for team in teams.get_all().values():
        balance=0
        wallet=wallets.get(team["wallet"])
        for asset in wallet["assets"]:
            if asset=="LTZ":
                balance+=wallet["assets"][asset]
                continue
            balance+=get_Price(asset)*wallet["assets"][asset]
        teams_List.append(team|{"balance":round(balance, 2)})
    teamsScript="<script>var teams="+json.dumps(teams_List)+"</script>"
    return render("index", locals()|globals())

@app.get("/leaderboard")
def leaderboard():
    data=[]
    for team in teams.get_all().values():
        balance=0
        wallet=wallets.get(team["wallet"])
        for asset in wallet["assets"]:
            if asset=="LTZ":
                balance+=wallet["assets"][asset]
                continue
            balance+=get_Price(asset)*wallet["assets"][asset]
        data.append({"name":team["name"], "people":team["people"], "balance":round(balance, 2)})
    data.sort(key=lambda x:x["balance"], reverse=True)
    team_Details=json.dumps(data)
    return render("leaderboard", locals()|globals())

def get_Price(asset):
    if asset=="LTZ":
        return 1
    return round(current_Prices[asset][-1], 2)

@app.get("/tradex")
def tradex_page():
    userAccount=auth()
    if not userAccount:
        return render("auth", locals()|globals())
    if userAccount["team"]=="":
        return {"error":"Create or Join a team first"}
    navbar=render("navbar", locals())
    teams_List=[]
    for team in teams.get_all().values():
        balance=0
        wallet=wallets.get(team["wallet"])
        for asset in wallet["assets"]:
            if asset=="LTZ":
                balance+=wallet["assets"][asset]
                continue
            balance+=get_Price(asset)*wallet["assets"][asset]
        teams_List.append(team|{"balance":balance})
    user_Wallet=wallets.get(userAccount["wallet"])
    user_Team=teams.get(userAccount["team"])
    team_Wallet=wallets.get(user_Team["wallet"])
    for asset in user_Wallet["assets"]:
        user_Wallet["assets"][asset]={"amount":user_Wallet["assets"][asset], "price":get_Price(asset)}
    for asset in team_Wallet["assets"]:
        team_Wallet["assets"][asset]={"amount":team_Wallet["assets"][asset], "price":get_Price(asset)}
    wallets_Dict={"Personal":user_Wallet["assets"], "Team":team_Wallet["assets"]}
    teamsScript="<script>var teams="+json.dumps(teams_List)+"</script>"
    walletsScript="<script>var wallets=Signal(\"wallets\", "+json.dumps(wallets_Dict)+")</script>"
    userAccount="<script>var userAccount="+json.dumps(userAccount)+"</script>"
    return render("tradex", locals()|globals())

@app.get("/auth")
def auth_api():
    args=dict(request.args)
    if "password" not in args or "username" not in args or "method" not in args:
        return {"error":"Missing Fields"}
    if args["method"]=="login":
        user_Account=users.get(args["username"])
        if user_Account==None:
            return {"error":"User '"+args["username"]+"' not found!"}
        if user_Account["password"]!=hashlib.sha256(args["password"].encode()).hexdigest():
            return {"error":"Passwords do not match"}
        return {"success":True, "error":""}
    else:
        user_Account=users.get(args["username"])
        if user_Account!=None:
            if user_Account["password"]==hashlib.sha256(args["password"].encode()).hexdigest():
                return {"success":True, "error":""}
            else:
                return {"error":"Incorrect Password"}
        else:
            wallet_Id=uuid.uuid4().__str__()
            base_Wallet=Wallet(id=wallet_Id, assets={"LTZ":0})
            wallets.set(wallet_Id, base_Wallet)
            base_User=User(name=args["username"], username=args["username"], password=hashlib.sha256(args["password"].encode()).hexdigest(), wallet=wallet_Id)
            users.set(args["username"], base_User)
            return {"success":True, "error":""}

@app.get("/create_team")
def create_team():
    args=dict(request.args)
    userAccount=auth()
    if userAccount and "name" in args:
        id=uuid.uuid4().__str__()
        wallet_Id=uuid.uuid4().__str__()
        base_Wallet=Wallet(id=wallet_Id, assets={"LTZ":100})
        wallets.set(wallet_Id, base_Wallet)
        new_Team=Team(id=id, name=args["name"], wallet=wallet_Id)
        teams.set(id, new_Team)
        return {"success":True}

@app.get("/join_team")
def join_team():
    args=dict(request.args)
    userAccount=auth()
    if userAccount and "id" in args:
        team=teams.get(args["id"])
        if team!=None:
            if len(team["people"])>1:
                return {"error":"too many people already in team"}
            else:
                team["people"].append(userAccount["username"])
                userAccount["team"]=args["id"]
                teams.set(team["id"], team)
        else:
            oldTeam=teams.get(userAccount["team"])
            if oldTeam!=None:
                oldTeam["people"]=[x for x in oldTeam["people"] if x!=userAccount["username"]]
                teams.set(oldTeam["id"], oldTeam)
            userAccount["team"]=""
        users.set(userAccount["username"], userAccount)
        return {"success":True}

@app.get("/prices")
def prices_api():
    args=dict(request.args)
    if "asset" in args:
        resp = app.response_class(json.dumps([round(x, 2) for x in current_Prices[args["asset"]]]))
    else:
        resp = app.response_class(json.dumps(dict([x, round(current_Prices[x][-1], 2)] for x in current_Prices)))
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

@app.get("/buy")
def buy_asset():
    args=dict(request.args)
    userAccount=auth()
    if userAccount and "assetA" in args and "assetB" in args and "amount" in args:
        team=teams.get(userAccount["team"])
        team_Wallet=wallets.get(team["wallet"])
        assetA=args["assetA"]
        assetB=args["assetB"]
        amount=float(args["amount"])
        if team_Wallet["assets"][assetA]<amount:
            return {"error":"Insufficient Funds"}
        team_Wallet["assets"][assetA]-=amount
        addAmount=(current_Prices[assetA][-1]/current_Prices[assetB][-1])*amount
        if assetB not in team_Wallet["assets"]:
            team_Wallet["assets"][assetB]=0
        team_Wallet["assets"][assetB]+=addAmount
        wallets.set(team_Wallet["id"], team_Wallet)
        return {"success":True}

@app.get("/send")
def send_assets():
    args=dict(request.args)
    userAccount=auth()
    if userAccount and "asset" in args and "amount" in args and "to" in args:
        teamA=teams.get(userAccount["team"])
        walletA=wallets.get(teamA["wallet"])
        walletB=wallets.get(args["to"])
        if walletB==None:
            return {"error":"to address account does not exist"}
        if walletA["assets"][args["asset"]]<float(args["amount"]):
            return {"error":"insufficient funds"}
        walletA["assets"][args["asset"]]-=float(args["amount"])
        if args["asset"] not in walletB["assets"]:
            walletB["assets"][args["asset"]]=0
        walletB["assets"][args["asset"]]+=float(args["amount"])
        wallets.set(walletA["id"], walletA)
        wallets.set(walletB["id"], walletB)
        return {"success":True}

@app.get("/chart")
def chart():
    return render("chart")

@app.get("/admin")
def admin():
    return render("admin",locals()|globals())

threading.Thread(target=calculate_Prices, daemon=True).start()

app.run(host="0.0.0.0", port=int(sys.argv[1]))