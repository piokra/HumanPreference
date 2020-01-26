import threading
from collections import deque
from queue import SimpleQueue, Empty, Full
from typing import Dict, Deque
import pika
from pika.exceptions import AMQPError


class DataQueue:
    _connection: pika.BlockingConnection = threading.local()
    _workers: int = 0
    _pop_data_queues: Dict[str, Deque] = {}
    _pop_dict_lock = threading.Lock()
    _push_queue = SimpleQueue()

    _qn_lock = threading.Lock()
    _qn_awaiting_handling = set()
    _handled_queue_names = set()
    _stop = False

    @classmethod
    def _set_up_connection(cls):
        from ..config import pika_username, pika_port, pika_host, pika_passwd
        credentials = pika.PlainCredentials(username=pika_username, password=pika_passwd)
        parameters = pika.ConnectionParameters(host=pika_host, port=pika_port,
                                               credentials=credentials)
        return pika.BlockingConnection(parameters)

    def __init__(self, queue_name):
        if DataQueue._workers == 0:
            DataQueue.start()

        self._queue_name = queue_name
        with DataQueue._qn_lock:
            if self._queue_name not in DataQueue._handled_queue_names:
                DataQueue._handled_queue_names.add(self._queue_name)
                DataQueue._qn_awaiting_handling.add(self._queue_name)

    @classmethod
    def start(cls):
        cls._workers += 1

        def _image_callback(qn, ch, methods, props, body):
            with DataQueue._pop_dict_lock:
                if qn not in DataQueue._pop_data_queues:
                    DataQueue._pop_data_queues[qn] = deque()
                DataQueue._pop_data_queues[qn].append(body)
            ch.basic_ack(delivery_tag=methods.delivery_tag)

        def _set_up_mq_queues(channel, queue_name):
            channel.queue_declare(queue_name + "_up", durable=True)
            channel.queue_declare(queue_name + "_down", durable=True, arguments={"x-max-length": 25})
            channel.basic_consume(queue=queue_name + "_down",
                                  on_message_callback=lambda *args: _image_callback(queue_name, *args))

        def _work():
            try:
                connection = cls._set_up_connection()
                channel = connection.channel()

                handled_queue_names = set()

                while not cls._stop:
                    with cls._qn_lock:
                        while len(cls._qn_awaiting_handling):
                            qn = cls._qn_awaiting_handling.pop()
                            handled_queue_names.add(qn)
                            _set_up_mq_queues(channel, qn)

                    while True:
                        try:
                            qn, body = cls._push_queue.get_nowait()
                            channel.basic_publish(exchange='', routing_key=qn + "_up",
                                                  body=body)
                        except Empty as e:
                            if not cls._push_queue.empty():
                                print(e)
                            break

                    connection.process_data_events(1)

            except AMQPError as e:
                print(e)
            cls._workers -= 1

        threading.Thread(target=_work).start()

    @classmethod
    def stop(cls):
        cls._stop = True

    def pop_data(self, limit=10):
        with DataQueue._pop_dict_lock:
            if self._queue_name in DataQueue._pop_data_queues:
                dq = DataQueue._pop_data_queues[self._queue_name]
                ret = []
                for _ in range(limit):
                    if len(dq) == 0:
                        return ret
                    ret.append(dq.popleft())
                return ret

    def push_data(self, data, result):
        try:
            DataQueue._push_queue.put_nowait((self._queue_name, "{}||{}".format(str(result), str(data))))
        except Full as e:
            print(e)

    @classmethod
    def inspect(cls):
        return repr(cls._pop_data_queues)
