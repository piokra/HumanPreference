from typing import Any, List

import pika


class DataQueue:
    images: List[Any]
    _connection: pika.BlockingConnection = None

    @classmethod
    def _set_up_connection(cls):
        from ..config import pika_username, pika_port, pika_host, pika_passwd
        credentials = pika.PlainCredentials(username=pika_username, password=pika_passwd)
        parameters = pika.ConnectionParameters(host=pika_host, port=pika_port,
                                               credentials=credentials)
        return pika.BlockingConnection(parameters)

    def __init__(self, queue_name):
        if DataQueue._connection is None or DataQueue._connection.is_closed:
            DataQueue._connection = DataQueue._set_up_connection()

        self.queue_name = queue_name

        self.channel = DataQueue._connection.channel()
        self.channel.basic_qos(prefetch_count=1)

        self.channel.queue_declare(queue_name + "_up", durable=True)
        self.channel.queue_declare(queue_name + "_down", durable=True)

        self.channel.basic_consume(queue=queue_name + "_down", on_message_callback=self._image_callback, auto_ack=True)
        self.images = []

    def await_data(self, timeout=None):
        while len(self.images) == 0:
            DataQueue._connection.process_data_events()

        ret = self.images[0]
        del self.images[0]
        return ret

    def push_data(self, data, result):
        self.channel.basic_publish(exchange='', routing_key=self.queue_name + "_up",
                                   body="{}|{}".format(str(result), str(data)))

    def _image_callback(self, ch, methods, props, body):
        self.images.append(body)
