import click
import socket
from kombu import Queue
from celery import Celery

from .message import Message
from .llm import reply, init_llm
from .models import set_default_model

init_llm("openai", False)
set_default_model("gpt-4o")

app = Celery(
    "devopsx", 
    broker="pyamqp://master:devopsx@5.8.93.225:5672//", 
    backend='rpc://',
    broker_heartbeat = 60,   # Send a heartbeat every 60 seconds
    broker_pool_limit = 10,  # Limit pool size as per environment capability
    broker_connection_timeout = 30,
    broker_connection_retry = True,
    broker_connection_max_retries = 100,
)

@app.task(name="DevopsxAssistant")
def chat(command: str):
    from .commands import execute_cmd, LogManager

    model = "gpt-4o"
    hostname = socket.gethostname()  
    
    log = LogManager()
    log.append(Message(role="user", content=command))    

    # if prompt is a user-command, execute it
    if log[-1].role == "user":
        # TODO: capture output of command and return it
        execute_cmd(log[-1], log, pty=False)
    
    # performs reduction/context trimming, if necessary
    msgs = log.prepare_messages()
 
    # generate response
    # TODO: add support for streaming
    msg = reply(msgs, model=model, stream=True)
    msg.quiet = True

    log.append(msg)
    msgs = log.prepare_messages()

    output_messages = "\n\n".join(msg.content for msg in msgs)
    return f"{hostname}\n\n{output_messages}"

@click.command("devopsx-celery")
@click.option(
    "-Q", "--queues", 
    multiple=True, 
    default=["default"], 
    help="Queues to consume"
)
def main(queues: list[str]):
    app.conf.update(
        accept_content = ['pickle', 'json', 'msgpack', 'yaml'],
        worker_send_task_events = True,
        task_default_queue = 'default',
        worker_hijack_root_logger = False,
        task_queues = (
            Queue('D1', routing_key='d1.#'),
            Queue('D2', routing_key='d2.#'),
            Queue('D3', routing_key='d3.#'),
            Queue('D4', routing_key='d4.#'),
            Queue('D5', routing_key='d5.#'),
            Queue('WEB', routing_key='web.#'),
        ),
        task_default_exchange = 'tasks',
        task_default_exchange_type = 'topic',
        task_default_routing_key = 'task.default'
    )

    args = ["worker", "-Q", ",".join(queues), "--loglevel=INFO"]
    app.worker_main(argv=args)