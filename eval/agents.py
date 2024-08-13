import os
from abc import abstractmethod

from devopsx import Message
from devopsx import chat as devopsx_chat
from devopsx import get_prompt

from .filestore import FileStore
from .types import Files


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
        store = FileStore()
        os.chdir(store.working_dir)  # can now modify store content

        if files:
            store.upload(files)

        print("\n--- Start of generation ---")
        print(f"Working in {store.working_dir}")
        prompt_sys = get_prompt()
        prompt_sys.content += (
            "\n\nIf you have trouble and dont seem to make progress, stop trying."
        )
        # TODO: add timeout
        try:
            devopsx_chat(
                [Message("user", prompt)],
                [prompt_sys],
                f"devopsx-evals-{store.id}",
                model=self.model,
                no_confirm=True,
                interactive=False,
            )
        # don't exit on sys.exit()
        except (SystemExit, KeyboardInterrupt):
            pass
        print("--- Finished generation ---\n")

        return store.download()
