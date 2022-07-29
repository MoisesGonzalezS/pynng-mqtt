"""
MQTT is used for synchronous communications where each question is responded with a single answer,
for example remote procedure calls (RPCs).
Like Pipeline, it also can perform load-balancing.
This is the only reliable messaging pattern in the suite, as it automatically will retry if a request is not matched with a response.

"""
import pynng
import curio

address = "mqtt-quic://127.0.0.1:14567"

async def main():
  with pynng.Mqtt(address) as mqtt:
    print(f"Make a connect msg")
    connmsg = pynng.Mqttmsg()
    connmsg.set_packet_type(1) # 0x01 Connect
    connmsg.set_connect_proto_version(4) # MqttV311
    await mqtt.asend_msg(connmsg)
    print(f"Connection packet sent.")
    pubmsg = pynng.Mqttmsg()
    pubmsg.set_packet_type(3) # 0x03 Publish
    pubmsg.set_publish_payload("Hello")
    pubmsg.set_publish_topic("topic")
    pubmsg.set_publish_qos(1) # qos is 1
    await mqtt.asend_msg(pubmsg)
    print(f"Publish packet sent.")

if __name__ == "__main__":
  try:
    curio.run(main)
  except KeyboardInterrupt:
    # that's the way the program *should* end
    exit(0)
