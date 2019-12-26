import sys

import pika

if __name__ == "__main__":
    sys.path.append('..')

    base64_image = r"""data:image/png;base64,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"""

    from config import pika_host, pika_passwd, pika_port, pika_username

    creds = pika.PlainCredentials(username=pika_username, password=pika_passwd)
    parameters = pika.ConnectionParameters(host=pika_host, port=pika_port, credentials=creds)
    connection = pika.BlockingConnection(parameters=parameters)
    channel = connection.channel()
    for _ in range(10):
        channel.basic_publish(exchange='', routing_key="Salto_down",
                              body="{}||{}".format(base64_image, base64_image))