from flask import request, redirect
from monster import render, tokeniser, parser, Flask
import sys, json
import litedb, hashlib

users=litedb.get_conn("users")
teams=litedb.get_conn("teams")
wallets=litedb.get_conn("wallets")
trades=litedb.get_conn("trades")
assets=litedb.get_conn("assets")

def Wallet(id="", balance=0):
    return {"id":id, "balancer":balance}

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

def auth():
    username=request.cookies.get("username")
    password=request.cookies.get("password")
    if username==None or password==None:
        return False
    user_Account=users.get(username)
    if user_Account==None:
        return False
    if user_Account["password"]==hashlib.sha256(password).hexdigest():
        return True
    return False

@app.get("/")
def home():
    if not auth():
        return render("auth", locals()|globals())
    navbar=render("navbar", locals())
    return render("index", locals()|globals())

@app.get("/auth")
def auth_api():
    return ""

app.run(host="0.0.0.0", port=int(sys.argv[1]))