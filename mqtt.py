import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import threading
import colorsys

from flask import Flask, jsonify, request, redirect
from flasgger import Swagger


app = Flask(__name__)
swagger = Swagger(app)

# MQTT broker details
broker_address = "broker.mqttdashboard.com"
broker_port = 1883
lamp = "" #Целевая лампа которой надо управлять
topic = "API" #Вторая лампа (она не управляется, через нее прнимаются данные)


def hsv_to_rgb_hex(h):
    s = 255
    v = 1
    r, g, b = [int(255 * x) for x in colorsys.hsv_to_rgb(h / 360, s, v)]
    return (r << 16) + (g << 8) + b


# Define a callback function to handle incoming messages
def on_message(client, userdata, message):
    payload_str = message.payload.decode('utf-8')
    if payload_str.startswith("GWL:1"):
        _, state, color, _ = payload_str.split(",")
        response = {"state": int(state), "color": int(color)}
        on_message.response = response
        on_message.event.set()


# Define a function to start the MQTT client in a separate thread
def start_mqtt_client():
    # Connect to the MQTT broker
    client = mqtt.Client()
    client.connect(broker_address, broker_port)

    # Subscribe to the MQTT topic and listen for incoming messages
    client.subscribe(topic)
    client.on_message = on_message
    client.loop_start()

@app.route("/", methods=["GET"])
def index():
    return redirect("/apidocs")

@app.route("/api/color", methods=["GET"])
def get_color():
    """
    Return color from lamp
    ---
    responses:
      200:
        description: Color in HEX RGB
        examples:
          {"value": -4248030465}
      501:
        description: Error with mqtt broker or lamp is unreacheable
        examples:
          {"value": "Something goes wrong. Try later"}
    """
    try:
        mqtt_thread = threading.Thread(target=start_mqtt_client)
        mqtt_thread.daemon = True
        mqtt_thread.start()

        client = mqtt.Client()
        client.connect(broker_address, broker_port)
        message = "GWL:2"
        publish.single(topic=lamp, payload=message, hostname=broker_address, port=broker_port)

        on_message.event = threading.Event()
        on_message.event.wait()

        response = on_message.response
        on_message.event.clear()

        return jsonify(501, {"value": hsv_to_rgb_hex(response['color'])}), 200
    except Exception as e:
        print(e)
        return jsonify({"value": "Something goes wrong. Try later"}), 502


@app.route("/api/state", methods=["GET"])
def get_state():
    """
    Return lamp state
    ---
    responses:
      200:
        description: Return lamp state (On/Off)
        examples:
          {"value": 1}
      501:
        description: Error with mqtt broker or lamp is unreacheable
        examples:
          {"value": "Something goes wrong. Try later"}
    """
    try:
        mqtt_thread = threading.Thread(target=start_mqtt_client)
        mqtt_thread.daemon = True
        mqtt_thread.start()

        client = mqtt.Client()
        client.connect(broker_address, broker_port)
        message = "GWL:2"
        publish.single(topic=lamp, payload=message, hostname=broker_address, port=broker_port)

        on_message.event = threading.Event()
        on_message.event.wait()

        response = on_message.response
        on_message.event.clear()

        return jsonify({"value": response['state']}), 200
    except Exception as e:
        print(e)
        return jsonify(501, {"value": "Something goes wrong. Try later"}), 502


@app.route("/api/setcolor", methods=["POST"])
def set_color():
    """
    Set lamp color
    ---
    parameters:
      - name: color
        in: formData
        type: int
        required: false
        default: 192
    responses:
      200:
        description: Color what now using
        examples:
          {"value": "Now color 192"}
      400:
        description: Color is not seted up
        examples:
          {"value": "Color is None"}
      502:
        description: Error with mqtt broker or lamp is unreacheable
        examples:
          {"value": "Something goes wrong. Try later"}
    """
    try:
        color = request.form.get('color')
        if color is not None:
            mqtt_thread = threading.Thread(target=start_mqtt_client)
            mqtt_thread.daemon = True
            mqtt_thread.start()

            client = mqtt.Client()
            client.connect(broker_address, broker_port)
            message = f"GWL:1,1,{color},0"
            publish.single(topic=lamp, payload=message, hostname=broker_address, port=broker_port)
            message = f"GWL:2"
            publish.single(topic=lamp, payload=message, hostname=broker_address, port=broker_port)
            on_message.event = threading.Event()
            on_message.event.wait()

            response = on_message.response
            on_message.event.clear()

            if response['color'] == color:
                return jsonify({"value": f"Now color {color}"}), 200
            else:
                return jsonify({"value": "Something goes wrong. Try later"}), 502
        else:
            return jsonify({"value": "Color is None"}), 400
    except Exception as e:
        print(e)
        return jsonify({"value": "Something goes wrong. Try later"}), 502


@app.route("/api/setstate", methods=["POST"])
def set_state():
    """
    Set lamp state
    ---
    parameters:
      - name: state
        in: formData
        type: int
        required: false
        default: 1
    responses:
      200:
        description: State of the lamp
        examples:
          {"value": "Now state 1"}
      400:
        description: lamp state is not seted up
        examples:
          {"value": "State is None"}
      501:
        description: Error with mqtt broker or lamp is unreacheable
        examples:
          {"value": "Something goes wrong. Try later"}
    """
    try:
        state = int(request.form.get('state'))
        if state is not None:
            mqtt_thread = threading.Thread(target=start_mqtt_client)
            mqtt_thread.daemon = True
            mqtt_thread.start()

            client = mqtt.Client()
            client.connect(broker_address, broker_port)
            message = f"GWL:2"
            publish.single(topic=lamp, payload=message, hostname=broker_address, port=broker_port)
            on_message.event = threading.Event()
            on_message.event.wait()

            response = on_message.response
            on_message.event.clear()
            message = f"GWL:1,{state},{response['color']},0"
            publish.single(topic=lamp, payload=message, hostname=broker_address, port=broker_port)

            message = f"GWL:2"
            publish.single(topic=lamp, payload=message, hostname=broker_address, port=broker_port)
            on_message.event = threading.Event()
            on_message.event.wait()

            response1 = on_message.response
            on_message.event.clear()
            if int(response1['state']) == int(state):
                return jsonify({"value": f"Now state {state}"}), 200
            else:
                return jsonify({"value": "Something goes wrong. Try later"}), 502
        else:
            return jsonify({"value": "State is None"}), 400
    except Exception as e:
        print(e)
        return jsonify({"value": "Something goes wrong. Try later"}), 502


@app.route("/api/wink", methods=["GET"])
def wink():
    """
    Wink with lamp
    ---
    responses:
      200:
        description: Wink with lamp
        examples:
          {"value": "Wink :)"}
      501:
        description: Error with mqtt broker or lamp is unreacheable
        examples:
          {"value": "Something goes wrong. Try later"}
    """
    try:
        mqtt_thread = threading.Thread(target=start_mqtt_client)
        mqtt_thread.daemon = True
        mqtt_thread.start()

        client = mqtt.Client()
        client.connect(broker_address, broker_port)
        message = f"GWL:2"
        publish.single(topic=lamp, payload=message, hostname=broker_address, port=broker_port)
        on_message.event = threading.Event()
        on_message.event.wait()

        response = on_message.response
        on_message.event.clear()

        message = f"GWL:1,1,{response['color']},1"
        publish.single(topic=lamp, payload=message, hostname=broker_address, port=broker_port)
        
        return jsonify({"value": "Wink :)"}), 200
    except Exception as e:
        print(e)
        return jsonify({"value": "Something goes wrong. Try later"}), 502

if __name__ == "__main__":
    app.run(port=8080)