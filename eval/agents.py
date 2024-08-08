import os
from abc import abstractmethod

from devopsx import Message
from devopsx import get_prompt
from devopsx import chat as devopsx_chat

from .types import Files
from .filestore import FileStore


class Agent:
    @abstractmethod
    def act(self, files: Files | None, prompt: str) -> Files:
        """
        Carries out the prompt and returns artifacts in the form of `Files`.
        """
        raise NotImplementedError


class DevopsxAgent(Agent):
    def act(self, files: Files | None, prompt: str):
        store = FileStore()
        os.chdir(store.working_dir)  # can now modify store content

        if files:
            store.upload(files)

        print("\n--- Start of generation ---")
        print(f"Working in {store.working_dir}")
        # TODO: add timeout
        try:
            devopsx_chat(
                [Message("user", prompt)],
                [get_prompt()],
                f"devopsx-evals-{store.id}",
                llm=None,
                model=None,
                no_confirm=True,
                interactive=False,
            )
        # don't exit on sys.exit()
        except (SystemExit, KeyboardInterrupt):
            pass
        print("--- Finished generation ---\n")

        return store.download()
