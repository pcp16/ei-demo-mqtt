# Mini práctica: MQTT local con Python

**Duración:** unos 30 minutos, con las dependencias instaladas previamente.
**Objetivo:** observar publicación/suscripción, comodines, QoS y mensajes retenidos.

Los tres programas se ejecutan en el mismo portátil:

```text
publicador.py ──► broker.py ──► suscriptor.py
                 127.0.0.1:1883
```

El broker usa aMQTT; los clientes, Eclipse Paho. Utilizamos **MQTT 3.1.1**, no MQTT 5.
El servidor escucha únicamente en este ordenador. Cada estudiante tiene su propio
broker: los mensajes no se intercambian con otros portátiles.

**Corrección de QoS:** `broker.py` incluye una adaptación local para aMQTT 0.12.1.
La biblioteca original reenvía publicaciones usando el QoS de la suscripción sin
limitarlo por el QoS publicado; también trata incorrectamente el QoS 0 de un retenido.
La adaptación conserva ese valor y aplica el mínimo correspondiente. No modifica
los paquetes instalados. El bloque `BrokerPractica` es infraestructura ya preparada:
no hay que editarlo durante la práctica. Sus métodos derivan de aMQTT, cuyo aviso
MIT se incluye en `LICENSE-amqtt.txt`. Se han probado las nueve combinaciones de
QoS 0/1/2 y la entrega tardía de un retenido QoS 0.

## 1. Preparación antes de clase

Necesitas **Python 3.10–3.14** e Internet para instalar las dependencias. Después,
la práctica funciona sin Internet. Descarga los tres `.py` en una misma carpeta y
abre una terminal dentro de ella. No llames a tus ficheros `mqtt.py`, `paho.py` o `amqtt.py`.

### Windows (PowerShell)

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install "amqtt==0.12.1" "paho-mqtt==2.1.0"
```

### macOS (Terminal)

```bash
python3 --version
python3 -m venv .venv
./.venv/bin/python -m pip install "amqtt==0.12.1" "paho-mqtt==2.1.0"
```

No necesitas activar el entorno ni permisos de administrador. En los ejemplos
siguientes, **sustituye `PYTHON` por la ruta de tu sistema**:

| Sistema | Sustitución de `PYTHON` |
|---|---|
| Windows | `.\.venv\Scripts\python.exe` |
| macOS | `./.venv/bin/python` |

Por ejemplo, `PYTHON broker.py` significa:

```powershell
# Windows
.\.venv\Scripts\python.exe broker.py
```

```bash
# macOS
./.venv/bin/python broker.py
```

## 2. Primer intercambio (5 minutos)

Abre **tres terminales en la carpeta de la práctica**. No cierres las dos primeras.

1. Terminal A: `PYTHON broker.py`. Espera a ver «Broker listo».
2. Terminal B: `PYTHON suscriptor.py`. Espera a ver «Suscripción».
3. Terminal C: `PYTHON publicador.py`.

El suscriptor mostrará algo parecido a:

```text
tema=aula/grupo01/temperatura | qos=0 | retain=False | {"valor":23.4,"unidad":"°C"}
```

**Pregunta:** ¿conoce el publicador la dirección o identidad del suscriptor?

## 3. Temas y comodines (5 minutos)

Sin cerrar el suscriptor, ejecuta en la terminal C:

```text
PYTHON publicador.py --tema aula/grupo02/temperatura --mensaje 25.8
PYTHON publicador.py --tema aula/grupo02/presencia --mensaje true
```

El filtro inicial `aula/+/temperatura` acepta el primer mensaje y no el segundo.
Detén el suscriptor con **Ctrl+C** y reinícialo así:

```text
PYTHON suscriptor.py --tema "aula/#"
```

Repite ambas publicaciones: ahora llegan las dos. Usa siempre comillas para los filtros.

- `+` sustituye exactamente un nivel.
- `#` sustituye cero o más niveles y aparece al final.
- Los comodines se utilizan al suscribirse, no al publicar.

## 4. Un mensaje, varios clientes (5 minutos)

En una cuarta terminal, abre otro `PYTHON suscriptor.py --tema "aula/#"`.
Publica una serie:

```text
PYTHON publicador.py --mensaje 24.0 --veces 5 --intervalo 2
```

Ambos suscriptores reciben los cinco mensajes. Son **cinco publicaciones nuevas**,
con el mismo contenido; no son retransmisiones MQTT. Cada envío de este publicador
abre y cierra su propia conexión para simplificar el código.

**Pregunta:** ¿hay que modificar el publicador para añadir un tercer suscriptor?

## 5. Mensajes retenidos (7 minutos)

Deja el broker abierto y detén todos los suscriptores con Ctrl+C. Usa este tema
exclusivo para el experimento. Primero elimina cualquier retenido anterior:

```text
PYTHON publicador.py --tema aula/demo/temperatura --borrar-retenido --qos 1
PYTHON publicador.py --tema aula/demo/temperatura --mensaje 23.4
PYTHON suscriptor.py --tema aula/demo/temperatura
```

**Resultado:** el suscriptor tardío no recibe el `23.4` pasado. Detén el suscriptor
y publica de nuevo, esta vez reteniendo el valor:

```text
PYTHON publicador.py --tema aula/demo/temperatura --mensaje 24.1 --retain --qos 1
PYTHON suscriptor.py --tema aula/demo/temperatura
```

**Resultado:** recibe inmediatamente `24.1`, con `retain=True`.
El broker conserva el último retenido de ese tema; no guarda un historial.

Para limpiar:

```text
PYTHON publicador.py --tema aula/demo/temperatura --borrar-retenido --qos 1
```

Esta opción envía **cero bytes con Retain activado**. Un suscriptor activo puede
ver ese mensaje vacío; un nuevo suscriptor ya no recibe el valor anterior.
Publicar normalmente con `retain=False` **no borra** un retenido existente.
Un mensaje publicado con Retain a un suscriptor ya activo suele llegar con
`retain=False` en MQTT 3.1.1: la marca del mensaje recibido indica aquí la entrega
del valor almacenado al suscribirse, no simplemente la opción usada por el publicador.

## 6. QoS y reconexión (5 minutos)

Con el suscriptor conectado y su QoS predeterminado 1:

```text
PYTHON publicador.py --mensaje 23.4 --qos 0
PYTHON publicador.py --mensaje 23.5 --qos 1
```

Observa el QoS mostrado. **En una conexión local estable los dos mensajes pueden
llegar una sola vez.** QoS 0 no fuerza pérdidas, y QoS 1 no fuerza duplicados.
La diferencia está en las confirmaciones y garantías. El QoS de la suscripción
es un máximo: no eleva una publicación QoS 0 a QoS 1.

Detén el suscriptor, publica un mensaje sin Retain en un tema nuevo y vuelve a
iniciarlo con ese tema. No recupera la publicación pasada. Una nueva publicación
sí llega. Estos clientes usan **sesiones limpias**, no colas persistentes durante
la desconexión. Retenidos y sesiones persistentes son mecanismos diferentes.

## Preguntas para entregar

Responde durante los experimentos. Para cada pregunta anota **predicción,
comandos utilizados, resultado observado y explicación** (2–4 líneas). Puedes
adjuntar un fragmento de salida de la terminal. No es necesario modificar el código.
Los experimentos 1–6 son obligatorios; 7–9 son ampliaciones si queda tiempo.

1. **Selección por tema.** Con `--tema "aula/+/temperatura"` en el suscriptor,
   publica en `aula/grupo01/temperatura`, `aula/grupo02/temperatura` y
   `aula/grupo02/presencia`. ¿Cuáles llegan? ¿Qué cambia con `--tema "aula/#"`?
2. **Profundidad de los niveles.** Publica en `aula/grupo01/sensor01/temperatura`.
   ¿Lo recibe `aula/+/temperatura`? Propón un filtro con `+` que sí lo reciba y
   compruébalo. ¿Qué diferencia hay respecto a `aula/#`?
3. **Varios receptores.** Abre dos suscriptores al mismo tema y publica una vez.
   ¿Recibe cada uno una copia o se reparten el mensaje? Cierra uno y publica de
   nuevo. ¿Has tenido que cambiar el publicador?
4. **Llegar tarde.** Utiliza el procedimiento de limpieza de la sección 5.
   Publica sin Retain antes de iniciar el suscriptor y repite con Retain.
   ¿En qué caso llega el valor pasado? ¿Quién lo conserva si el publicador ya terminó?
5. **Último valor o historial.** Sin suscriptor activo, publica `20`, `21` y `22`
   en `aula/demo/temperatura`, todos con `--retain --qos 1`. Inicia el suscriptor.
   ¿Recibe uno o tres valores? Bórralo con `--borrar-retenido` y vuelve a iniciar
   el suscriptor. ¿Qué cambia?
6. **QoS de publicación y suscripción.** Suscríbete primero con `--qos 1` y
   publica una vez con QoS 0 y otra con QoS 1. Repite con el suscriptor en QoS 0.
   Completa la tabla. ¿Que no observes pérdidas o duplicados demuestra que QoS 0
   y QoS 1 ofrecen la misma garantía? Justifica tu respuesta.

   | QoS publicado | QoS solicitado al suscribirse | QoS recibido | Número de entregas |
   |---|---|---|---|
   | 0 | 1 | | |
   | 1 | 1 | | |
   | 0 | 0 | | |
   | 1 | 0 | | |

7. **Contenido frente a estructura.** Sin cambiar el tema, publica `20` y `30`.
   ¿El filtro selecciona mensajes por su valor? ¿Dónde añadirías una condición
   para mostrar únicamente temperaturas superiores a 25?
8. **Retenido frente a publicación normal.** Sin suscriptor activo, guarda `20`
   con Retain y después publica `30` sin Retain en el mismo tema. Suscríbete.
   ¿Qué recibes? ¿Es necesariamente la última publicación que se hizo en ese tema?
9. **Reconexión y reinicio.** En un tema sin retenido, cierra el suscriptor,
   publica con QoS 1 y vuelve a abrirlo. ¿Recupera ese mensaje? Después guarda un
   retenido, detén todos los programas y reinicia broker y suscriptor. ¿Persiste
   el retenido? Relaciona los resultados con la sesión limpia y el almacenamiento
   en memoria de esta configuración.

## Opciones y cambios en el código

No hace falta editar los ficheros: utiliza las opciones siguientes. Para modificar
un valor predeterminado, cambia el argumento `default=` de su `add_argument(...)`.
Mantén la configuración de red y los callbacks sin cambios durante esta práctica.

| Programa | Opciones |
|---|---|
| Todos | `--puerto 1884` para utilizar otro puerto local |
| Suscriptor | `--tema "aula/#"`, `--qos 0`, `--qos 1` o `--qos 2` |
| Publicador | `--tema`, `--mensaje`, `--qos`, `--retain`, `--borrar-retenido` |
| Publicador | `--veces 5 --intervalo 2` para repetir el envío |

`--mensaje` admite texto o números. El valor predeterminado es un JSON de ejemplo;
no es necesario pelearse con comillas JSON en la terminal. `--borrar-retenido`
ignora `--mensaje`. Para consultar la ayuda: `PYTHON publicador.py --help`.

## Si algo falla

- **No conecta:** arranca primero el broker; comprueba que todos usan el mismo puerto.
- **Puerto ocupado:** usa `--puerto 1884` en los tres programas.
- **No aparece el mensaje:** comprueba el filtro y espera a que se confirme la
  suscripción antes de publicar; los temas distinguen mayúsculas y minúsculas.
- **Falta un módulo:** ejecuta con el Python de `.venv`, no con otro intérprete.
- **`py` no existe en Windows:** prueba `python --version` y, si cumple el requisito,
  usa `python -m venv .venv`.
- **Python es antiguo:** instala una versión compatible antes de clase o trabaja en pareja.

Finaliza los procesos con **Ctrl+C**, dejando el broker para el final. En esta
configuración el estado se mantiene en memoria: detener y arrancar el broker
elimina los retenidos. No estamos configurando almacenamiento en disco ni TLS;
el broker solo acepta conexiones desde el propio portátil.

## Referencias

- [aMQTT: versiones y requisitos](https://pypi.org/project/amqtt/)
- [API del broker aMQTT](https://amqtt.readthedocs.io/en/latest/references/broker/)
- [Eclipse Paho MQTT para Python](https://eclipse.dev/paho/clients/python/docs/)
