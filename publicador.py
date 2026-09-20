"""Publica un mensaje o una serie de mensajes en un tema MQTT."""
import argparse
import time
import uuid

from paho.mqtt import publish
import paho.mqtt.client as mqtt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tema", default="aula/grupo01/temperatura")
    parser.add_argument("--mensaje", default='{"valor":23.4,"unidad":"°C"}')
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], default=0)
    parser.add_argument("--retain", action="store_true", help="Guardar como último retenido")
    parser.add_argument("--borrar-retenido", action="store_true",
                        help="Enviar cero bytes con retain; ignora --mensaje")
    parser.add_argument("--veces", type=int, default=1)
    parser.add_argument("--intervalo", type=float, default=2.0, help="Segundos entre envíos")
    parser.add_argument("--puerto", type=int, default=1883)
    args = parser.parse_args()
    if not args.tema or any(c in args.tema for c in "+#\x00"):
        parser.error("Publica en un tema concreto, sin comodines ni caracteres nulos.")
    if args.veces < 1 or args.intervalo < 0:
        parser.error("--veces debe ser positivo y --intervalo no puede ser negativo.")
    contenido = b"" if args.borrar_retenido else args.mensaje
    retenido = args.retain or args.borrar_retenido
    try:
        for i in range(args.veces):
            # single abre una conexión, completa el envío y se desconecta.
            publish.single(
                args.tema, payload=contenido, qos=args.qos, retain=retenido,
                hostname="127.0.0.1", port=args.puerto,
                client_id=f"alumno-pub-{uuid.uuid4().hex[:12]}",
                protocol=mqtt.MQTTv311,
            )
            print(f"Enviado {i + 1}/{args.veces}: {args.tema} | "
                  f"qos={args.qos} | retain={retenido} | {contenido}", flush=True)
            if i + 1 < args.veces:
                time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nPublicador detenido.")
    except OSError as error:
        raise SystemExit(f"No se pudo publicar. Comprueba el broker y el puerto. Detalle: {error}")


if __name__ == "__main__":
    main()
