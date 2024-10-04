import logging
from abc import abstractmethod

from devopsx import Message
from devopsx import chat as devopsx_chat
from devopsx import get_prompt
from devopsx.cli import get_name
from devopsx.dirs import get_logs_dir
from devopsx.tools import init_tools

from .filestore import FileStore
from .types import Files

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def act(self, files: Files | None, prompt: str) -> Files:
        """
        Carries out the prompt and returns artifacts in the form of `Files`.
        """
        raise NotImplementedError


class DevopsxAgent(Agent):
    def act(self, files: Files | None, prompt: str):
        _id = abs(hash(prompt)) % 1000000
        name = get_name(f"devopsx-evals-{self.model.replace('/', '--')}-{_id}")
        log_dir = get_logs_dir() / name
        workspace_dir = log_dir / "workspace"
        if workspace_dir.exists():
            raise FileExistsError(
                f"Workspace directory {workspace_dir} already exists."
            )

        store = FileStore(working_dir=workspace_dir)
        if files:
            store.upload(files)

        # TODO: make eval toolset configurable
        init_tools()

        print("\n--- Start of generation ---")
        logger.debug(f"Working in {store.working_dir}")
        prompt_sys = get_prompt()
        prompt_sys = prompt_sys.replace(
            content=prompt_sys.content
            + "\n\nIf you have trouble and dont seem to make progress, stop trying."
        )
        try:
            devopsx_chat(
                [Message("user", prompt)],
                [prompt_sys],
                logdir=log_dir,
                model=self.model,
                no_confirm=True,
                interactive=False,
                workspace=workspace_dir,
            )
        # don't exit on sys.exit()
        except (SystemExit, KeyboardInterrupt):
            pass
        print("--- Finished generation ---\n")

        return store.download()