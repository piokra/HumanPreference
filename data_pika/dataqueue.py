import threading

import pika
from pika.exceptions import AMQPError


class DataQueue:
    _connection: pika.BlockingConnection = threading.local()
    _data_queues = {}

    @classmethod
    def _set_up_connection(cls):
        from ..config import pika_username, pika_port, pika_host, pika_passwd
        credentials = pika.PlainCredentials(username=pika_username, password=pika_passwd)
        parameters = pika.ConnectionParameters(host=pika_host, port=pika_port,
                                               credentials=credentials)
        return pika.BlockingConnection(parameters)

    def __init__(self, queue_name):
        if not hasattr(DataQueue._connection,
                       'value') or DataQueue._connection.value is None or DataQueue._connection.value.is_closed:
            DataQueue._connection.value = DataQueue._set_up_connection()
        else:
            try:
                DataQueue._connection.value.process_data_events()
            except AMQPError:
                DataQueue._connection.value = DataQueue._set_up_connection()

        self._queue_name = queue_name

        self._channel = DataQueue._connection.value.channel()
        # self.channel.basic_qos(prefetch_count=1)

        self._channel.queue_declare(queue_name + "_up", durable=True)
        self._channel.queue_declare(queue_name + "_down", durable=True)

        self._channel.basic_consume(queue=queue_name + "_down", on_message_callback=self._image_callback)

    def await_data(self, timeout=None):
        while self._queue_name not in DataQueue._data_queues or len(DataQueue._data_queues[self._queue_name]) == 0:
            DataQueue._connection.value.process_data_events()

        ret = DataQueue._data_queues[self._queue_name].pop(0)
        return ret

    def push_data(self, data, result):
        self._channel.basic_publish(exchange='', routing_key=self._queue_name + "_up",
                                    body="{}|{}".format(str(result), str(data)))

    def _image_callback(self, ch, methods, props, body):
        if self._queue_name not in DataQueue._data_queues:
            prin("Creating new data queue {}".format(self._queue_name))
            DataQueue._data_queues[self._queue_name] = []
        DataQueue._data_queues[self._queue_name].append(body)
        ch.basic_ack(delivery_tag=methods.delivery_tag)

    @classmethod
    def inspect(cls):
        return repr(cls._data_queues)

    def close(self):
        if self._channel is not None:
            self._channel.close()
            self._channel = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
