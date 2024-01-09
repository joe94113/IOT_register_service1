from flask import Flask, render_template, request, redirect, url_for
from flask import session
from flask import jsonify
import paho.mqtt.client as mqtt
import time
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MQTT 客戶端設置
def on_connect(client, userdata, flags, rc):
    global flag_connected
    flag_connected = 1
    print("Connected to MQTT server")

def on_disconnect(client, userdata, rc):
    global flag_connected
    flag_connected = 0
    print("Disconnected from MQTT server")

def on_message_joe_service_register(client, userdata, msg):
    global current_user
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        username = data.get('username')

        if username and username == current_user:
            input_device = data['devicePair']['inputDevice']
            output_devices = data['devicePair']['outputDevices']

            users = read_json("users.json")
            users[current_user]['inputDevice'] = input_device
            users[current_user]['outputDevices'] = output_devices

            write_json(users, "users.json")
            print(f"Device info updated for user: {current_user}")

    except Exception as e:
        print(f"Error processing message: {e}")

# 替換為您的 MQTT 伺服器地址
MQTT_BROKER_ADDRESS = 'broker.MQTTGO.io'

client = mqtt.Client("joe_client")  # 替換為您的客戶端名稱
flag_connected = 0
current_user = ''
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.message_callback_add('joe/service/register', on_message_joe_service_register)
client.connect(MQTT_BROKER_ADDRESS, 1883, 60)  # 連接 MQTT 伺服器
client.loop_start()
# Helper function to read/write JSON data
def read_json(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def write_json(data, filename):
    with open(filename, 'w') as file:
        json.dump(data, file)

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        users = read_json("tmp/users.json")
        if username not in users:
            users[username] = {'enabled': False}
            write_json(users, "tmp/users.json")
            return redirect(url_for('login'))
        else:
            return "<p>Username already exists.</p> and <a href='/login'>Login</a>"
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    global current_user
    if request.method == "POST":
        username = request.form["username"]
        users = read_json("tmp/users.json")
        if username in users:
            session['username'] = username
            current_user = username
            return redirect(url_for('admin'))
        else:
            return "<p>Username not found. Please register.</p> and <a href='/register'>Register</a>"
    return render_template("login.html")

# show all user device
@app.route("/device", methods=["GET"])
def device():
    users = read_json("tmp/users.json")
    for user in users:
        if 'inputDevice' not in users[user]:
            users[user]['inputDevice'] = {}
        if 'outputDevices' not in users[user]:
            users[user]['outputDevices'] = []
        inputDevice = users[user]['inputDevice']
        outputDevices = users[user]['outputDevices']
        # inputDevice to dictionary
        inputDeviceDict = {}
        for device in inputDevice:
            inputDeviceDict[device] = inputDevice[device]
        typeDict = {
            'flameAlarm': '火災警報',
            'earthquakeAlarm': '地震警報',
            'temperature': '溫度',
            'humidity': '濕度',
            'airConditionerTemperature': '冷氣溫度',
        }
        for device in outputDevices:
            if device['type'] in typeDict:
                device['type'] = typeDict[device['type']]
        users[user]['inputDevice'] = inputDeviceDict
    print(users)
    return render_template("device.html", users=users)

# 切換用戶啟用狀態的路由
@app.route("/toggle_user_status", methods=["POST"])
def toggle_user_status():
    data = request.json
    username = data.get('username')

    users = read_json("tmp/users.json")

    if username in users:
        print(users[username]);
        users[username]['enabled'] = users[username]['enabled'] ^ True
        write_json(users, "tmp/users.json")
        return jsonify({"message": "User status updated successfully."}), 200

    return jsonify({"error": "User not found."}), 404

@app.route("/logout", methods=["GET", "POST"])
def logout():
    global current_user
    session.pop('username', None)
    current_user = ''
    return redirect(url_for('index'))

@app.route("/admin")
def admin():
    global current_user
    # check current_user exists
    if 'username' in session:
        current_user = session['username']
        # 用戶已登入，這裡可以添加 MQTT 相關的代碼來處理訂閱
        global flag_connected
        if flag_connected:
            print("Subscribing to joe/service/register")
            client.subscribe("joe/service/register")
            # return "<p>Welcome to the admin page!</p>"
            users = read_json("tmp/users.json")
            if current_user in users:
                if 'inputDevice' not in users[current_user]:
                    users[current_user]['inputDevice'] = {}
                if 'outputDevices' not in users[current_user]:
                    users[current_user]['outputDevices'] = []
                inputDevice = users[current_user]['inputDevice']
                outputDevices = users[current_user]['outputDevices']
                # inputDevice to dictionary
                inputDeviceDict = {}
                for device in inputDevice:
                    inputDeviceDict[device] = inputDevice[device]
                typeDict = {
                    'flameAlarm': '火災警報',
                    'earthquakeAlarm': '地震警報',
                    'temperature': '溫度',
                    'humidity': '濕度',
                    'airConditionerTemperature': '冷氣溫度',
                }
                for device in outputDevices:
                    if device['type'] in typeDict:
                        device['type'] = typeDict[device['type']]
                return render_template("admin.html", username=current_user, inputDevice=inputDeviceDict, outputDevices=outputDevices)
            else:
                return "<p>Username not found. Please publish to joe/service/register register.</p>"
        else:
            return "<p>MQTT Server not connected. Please try again later.</p>"
    else:
        return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True, threaded=True)

