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
    connmsg.set_connect_keep_alive(60)
    connmsg.set_connect_clean_session(True)
    await mqtt.asend_msg(connmsg)
    print(f"Connection packet sent.")
    submsg = pynng.Mqttmsg()
    submsg.set_packet_type(8) # 0x08 Subscribe
    submsg.set_subscribe_topic("topic", 1) # topic With Qos 1
    await mqtt.asend_msg(submsg)
    print(f"Subscribe packet sent.")
    while True:
      rmsg = await mqtt.arecv_msg()
      rmsg.__class__ = pynng.Mqttmsg # convert to mqttmsg
      print("msg", rmsg, "arrived.")
      print("type:   ", rmsg.packet_type())
      print("qos:    ", rmsg.publish_qos())
      print("topic:  ", rmsg.publish_topic())
      print("payload:", rmsg.publish_payload())

if __name__ == "__main__":
  try:
    curio.run(main)
  except KeyboardInterrupt:
    # that's the way the program *should* end
    exit(0)
