import logging

import click

from .init import PROVIDERS, init, init_logging

logger = logging.getLogger(__name__)


@click.command("devopsx-server")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output.")
@click.option(
    "--llm",
    default=None,
    help="LLM provider to use.",
    type=click.Choice(["openai", "azure", "google", "groq", "anthropic", "local"]),
)
@click.option(
    "--model",
    default=None,
    help="Model to use by default, can be overridden in each request.",
)
def main(verbose: bool, llm: str | None, model: str | None):  # pragma: no cover
    """
    Starts a server and web UI for devopsx.

    Note that this is very much a work in progress, and is not yet ready for normal use.
    """
    init_logging(verbose)
    init(llm, model, interactive=False)

    # if flask not installed, ask the user to install `server` extras
    try:
        __import__("flask")
    except ImportError:
        logger.error(
            "devopsx installed without needed extras for server. "
            "Install them with `pip install devopsx-python[server]`"
        )
        exit(1)
    click.echo("Initialization complete, starting server")

    # noreorder
    from devopsx.server import main as server_main  # fmt: skip
    server_main()
