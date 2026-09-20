"""Muestra publicaciones que coinciden con un filtro MQTT."""
import argparse
import uuid

import paho.mqtt.client as mqtt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tema", default="aula/+/temperatura")
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], default=1)
    parser.add_argument("--puerto", type=int, default=1883)
    args = parser.parse_args()

    def conectado(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"Conexión rechazada: {reason_code}", flush=True)
            client.disconnect()
            return
        client.subscribe(args.tema, qos=args.qos)

    def suscrito(client, userdata, mid, reason_codes, properties):
        print(f"Suscripción: {args.tema} | resultado: {reason_codes}", flush=True)

    def recibido(client, userdata, msg):
        contenido = msg.payload.decode("utf-8", errors="replace")
        print(f"tema={msg.topic} | qos={msg.qos} | retain={msg.retain} | {contenido}",
              flush=True)

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"alumno-sub-{uuid.uuid4().hex[:12]}",
        clean_session=True,
        protocol=mqtt.MQTTv311,
    )
    client.on_connect = conectado
    client.on_subscribe = suscrito
    client.on_message = recibido
    try:
        client.connect("127.0.0.1", args.puerto, keepalive=30)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nSuscriptor detenido.")
    except OSError as error:
        raise SystemExit(f"No se pudo conectar. Arranca primero el broker. Detalle: {error}")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
