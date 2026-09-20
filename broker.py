"""Broker MQTT 3.1.1 local. Ejecutar primero y dejar abierto."""
from __future__ import annotations
from importlib.metadata import version
from amqtt.events import BrokerEvents
from amqtt.broker import Action, QOS_1, QOS_2, format_client_message

import argparse
import asyncio
import logging

from amqtt.broker import Broker


# Compatibilidad exclusiva para aMQTT 0.12.1: preservar y limitar el QoS.
# Métodos adaptados de amqtt/broker.py (licencia MIT).
# Copyright (c) 2015 Nicolas Jouanin; (c) 2020 aMQTT Contributors.
# Véase LICENSE-amqtt.txt para el aviso completo.
# Este bloque es infraestructura docente; no es un ejercicio del alumnado.
class BrokerPractica(Broker):
    async def _handle_message_delivery(
        self,
        client_session: Session,
        handler: BrokerProtocolHandler,
        wait_deliver: asyncio.Future[Any],
    ) -> bool:
        """Handle message delivery to the client."""
        self.logger.debug(f"{client_session.client_id} handling message delivery")
        app_message = wait_deliver.result()

        # notify of a message's receipt, even if a client isn't necessarily allowed to send it
        await self.plugins_manager.fire_event(
            BrokerEvents.MESSAGE_RECEIVED,
            client_id=client_session.client_id,
            message=app_message,
        )

        if app_message is None:
            self.logger.debug("app_message was empty!")
            return True
        if not app_message.topic:
            self.logger.warning(
                f"[MQTT-4.7.3-1] - {client_session.client_id} invalid TOPIC sent in PUBLISH message, closing connection",
            )
            return False
        if "#" in app_message.topic or "+" in app_message.topic:
            self.logger.warning(
                f"[MQTT-3.3.2-2] - {client_session.client_id} invalid TOPIC sent in PUBLISH message, closing connection",
            )
            return False
        if app_message.topic.startswith("$"):
            self.logger.warning(
                f"[MQTT-4.7.2-1] - {client_session.client_id} cannot use a topic with a leading $ character."
            )
            return False

        permitted = await self._topic_filtering(client_session, topic=app_message.topic, action=Action.PUBLISH)
        if not permitted:
            self.logger.info(f"{client_session.client_id} not allowed to publish to TOPIC {app_message.topic}.")
        else:
            # notify that a received message is valid and is allowed to be distributed to other clients
            await self.plugins_manager.fire_event(
                BrokerEvents.MESSAGE_BROADCAST,
                client_id=client_session.client_id,
                message=app_message,
            )
            await self._broadcast_message(client_session, app_message.topic, app_message.data, app_message.qos)
            if app_message.publish_packet and app_message.publish_packet.retain_flag:
                await self.retain_message(client_session, app_message.topic, app_message.data, app_message.qos)
        return True

    async def _run_broadcast(self, running_tasks: deque[asyncio.Task[OutgoingApplicationMessage]]) -> None:
        """Process a single broadcast message."""
        broadcast = await self._broadcast_queue.get()

        self.logger.debug(f"Processing broadcast message: {broadcast}")

        for k_filter, subscriptions in self._subscriptions.items():

            # Skip all subscriptions which do not match the topic
            if not self._matches(broadcast["topic"], k_filter):
                self.logger.debug(f"Topic '{broadcast['topic']}' does not match filter '{k_filter}'")
                continue

            for target_session, sub_qos in subscriptions:
                qos = min(broadcast.get("qos", sub_qos), sub_qos)

                sendable = await self._topic_filtering(target_session, topic=broadcast["topic"], action=Action.RECEIVE)
                if not sendable:
                    self.logger.info(
                        f"{target_session.client_id} not allowed to receive messages from TOPIC {broadcast['topic']}.")
                    continue

                # Retain all messages which cannot be broadcasted, due to the session not being connected
                #  but only when clean session is false and qos is 1 or 2 [MQTT 3.1.2.4]
                #  and, if a client used anonymous authentication, there is no expectation that messages should be retained
                if (target_session.transitions.state != "connected"
                        and not target_session.clean_session
                        and qos in (QOS_1, QOS_2)
                        and not target_session.is_anonymous):
                    self.logger.debug(f"Session {target_session.client_id} is not connected, retaining message.")
                    await self._retain_broadcast_message(broadcast, qos, target_session)
                    continue

                # Only broadcast the message to connected clients
                if target_session.transitions.state != "connected":
                    continue

                self.logger.debug(
                    f"Broadcasting message from {format_client_message(session=broadcast['session'])}"
                    f" on topic '{broadcast['topic']}' to {format_client_message(session=target_session)}",
                )

                handler = self._get_handler(target_session)
                if handler:
                    task = asyncio.ensure_future(
                        handler.mqtt_publish(
                            broadcast["topic"],
                            broadcast["data"],
                            qos,
                            retain=False,
                        ),
                    )
                    running_tasks.append(task)

    async def _publish_retained_messages_for_subscription(self, subscription: tuple[str, int], session: Session) -> None:
        self.logger.debug(
            f"Begin broadcasting messages retained due to subscription on '{subscription[0]}'"
            f" from {format_client_message(session=session)}",
        )
        publish_tasks = []

        topic_filter, qos = subscription
        for topic, retained in self._retained_messages.items():
            self.logger.debug(f"matching : {topic} {topic_filter}")
            if self._matches(topic, topic_filter):
                self.logger.debug(f"{topic} and {topic_filter} match")
                handler = self._get_handler(session)
                if handler:
                    publish_tasks.append(
                        asyncio.Task(
                            handler.mqtt_publish(retained.topic, retained.data, min(qos, retained.qos if retained.qos is not None else qos), retain=True),
                        ),
                    )
        if publish_tasks:
            await asyncio.wait(publish_tasks)
        self.logger.debug(
            f"End broadcasting messages retained due to subscription on '{subscription[0]}'"
            f" from {format_client_message(session=session)}",
        )


async def ejecutar(puerto):
    if version("amqtt") != "0.12.1":
        raise RuntimeError("Esta práctica requiere amqtt==0.12.1")
    broker = BrokerPractica({
        "listeners": {"default": {
            "type": "tcp", "bind": f"127.0.0.1:{puerto}"
        }},
        "plugins": {
            "amqtt.plugins.authentication.AnonymousAuthPlugin": {
                "allow_anonymous": True
            }
        },
    })
    await broker.start()
    print(f"Broker listo en 127.0.0.1:{puerto}. Ctrl+C para detenerlo.", flush=True)
    try:
        await asyncio.Event().wait()
    finally:
        await broker.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puerto", type=int, default=1883)
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    try:
        asyncio.run(ejecutar(args.puerto))
    except KeyboardInterrupt:
        print("Broker detenido.")
