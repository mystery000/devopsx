import socket
from kombu import Queue
from celery import Celery

from ..message import Message
from ..llm import reply, init_llm
from ..models import set_default_model

init_llm("openai", False)
set_default_model("gpt-4o")

app = Celery("devopsx", broker="pyamqp://master:devopsx@5.8.93.225//", backend='rpc://')
app.conf.accept_content = ['pickle', 'json', 'msgpack', 'yaml']
app.conf.worker_send_task_events = True
app.conf.task_default_queue = 'default'

app.conf.task_queues = (
    Queue('D1',  routing_key='d1.#'),
    Queue('D2',  routing_key='d2.#'),
    Queue('D3',  routing_key='d3.#'),
    Queue('D4',  routing_key='d4.#'),
    Queue('D5',  routing_key='d5.#'),
    Queue('WEB', routing_key='web.#'),
)

app.conf.task_default_exchange = 'tasks'
app.conf.task_default_exchange_type = 'topic'
app.conf.task_default_routing_key = 'task.default'

@app.task(name="Devopsx Assistant")
def devopsx_reply(prompt: str):
    hostname = socket.gethostname()  
    message = reply([Message(role='user', content=prompt)], model="gpt-4o")
    return f"{hostname}: {message.content}"

