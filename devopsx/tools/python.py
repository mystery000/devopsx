import atexit
import logging
import urllib.parse
from dataclasses import dataclass

from playwright.sync_api import ElementHandle, Page, sync_playwright

from collections.abc import Generator
from logging import getLogger

from IPython.terminal.embed import InteractiveShellEmbed
from IPython.utils.io import capture_output

from ..message import Message
from ..util import ask_execute, print_preview

from .save import execute_save

_ipython = None
_p = None

logger = logging.getLogger(__name__)

def init_python():
    check_available_packages()


def execute_python(code: str, ask: bool) -> Generator[Message, None, None]:
    """Executes a python codeblock and returns the output."""
    code = code.strip()
    if ask:
        print_preview(code, "python")
        confirm = ask_execute()
        print()
        if not confirm:
            # early return
            # yield Message("system", "Aborted, user chose not to run command.")
            # return
            yield from execute_save("save.py", code, ask=ask)
            return
    else:
        print("Skipping confirmation")

    # Create an IPython instance if it doesn't exist yet
    global _ipython
    if _ipython is None:
        _ipython = InteractiveShellEmbed()

    # Capture the standard output and error streams
    with capture_output() as captured:
        # Execute the code
        result = _ipython.run_cell(code)

    output = ""
    if captured.stdout:
        output += f"stdout:\n```\n{captured.stdout.rstrip()}\n```\n\n"
    if captured.stderr:
        output += f"stderr:\n```\n{captured.stderr.rstrip()}\n```\n\n"
    if result.error_in_exec:
        tb = result.error_in_exec.__traceback__
        while tb.tb_next:  # type: ignore
            tb = tb.tb_next  # type: ignore
        output += f"Exception during execution on line {tb.tb_lineno}:\n  {result.error_in_exec.__class__.__name__}: {result.error_in_exec}"  # type: ignore
    if result.result is not None:
        output += f"Result:\n```\n{result.result}\n```\n\n"
    yield Message("system", "Executed code block.\n\n" + output)


def check_available_packages():
    """Checks that essentials like numpy, pandas, matplotlib are available."""
    expected = ["numpy", "pandas", "matplotlib"]
    missing = []
    for package in expected:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    if missing:
        logger.warning(
            f"Missing packages: {', '.join(missing)}. Install them with `pip install gptme-python -E datascience`"
        )

def get_browser():
    """
    Return a browser object.
    """
    global _p
    if _p is None:
        logger.info("Starting browser")
        _p = sync_playwright().start()

        atexit.register(_p.stop)
    browser = _p.chromium.launch()
    return browser


def load_page(url: str) -> Page:
    browser = get_browser()

    # set browser language to English such that Google uses English
    coords_sf = {"latitude": 37.773972, "longitude": 13.39}
    context = browser.new_context(
        locale="en-US",
        geolocation=coords_sf,
        permissions=["geolocation"],
    )

    # create a new page
    logger.info(f"Loading page: {url}")
    page = context.new_page()
    page.goto(url)

    return page


def search_google(query: str) -> str:
    query = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={query}&hl=en"
    page = load_page(url)

    els = _list_clickable_elements(page)
    for el in els:
        # print(f"{el['type']}: {el['text']}")
        if "Accept all" in el.text:
            el.element.click()
            logger.debug("Accepted Google terms")
            break

    # list results
    result_str = _list_results_google(page)

    return result_str


def search_duckduckgo(query: str) -> str:
    url = f"https://duckduckgo.com/?q={query}"
    page = load_page(url)

    return _list_results_duckduckgo(page)


@dataclass
class Element:
    type: str
    text: str
    name: str
    href: str | None
    element: ElementHandle
    selector: str

    @classmethod
    def from_element(cls, element: ElementHandle):
        return cls(
            type=element.evaluate("el => el.type"),
            text=element.evaluate("el => el.innerText"),
            name=element.evaluate("el => el.name"),
            href=element.evaluate("el => el.href"),
            element=element,
            # FIXME: is this correct?
            selector=element.evaluate("el => el.selector"),
        )


def _list_input_elements(page) -> list[Element]:
    # List all input elements
    elements = []
    inputs = page.query_selector_all("input")
    for input_element in inputs:
        elements.append(Element.from_element(input_element))
    return elements


def _list_clickable_elements(page, selector=None) -> list[Element]:
    elements = []

    # filter by selector
    if selector:
        selector = f"{selector} button, {selector} a"
    else:
        selector = "button, a"

    # List all clickable buttons
    clickable = page.query_selector_all(selector)
    for i, el in enumerate(clickable):
        # "selector": f"{tag_name}:has-text('{text}')",
        elements.append(Element.from_element(el))

    return elements


def _list_results_google(page) -> str:
    # fetch the results (elements with .g class)
    results = page.query_selector_all(".g")
    if not results:
        return "Error: something went wrong with the search."

    # list results
    s = "Results:"
    for i, result in enumerate(results):
        url = result.query_selector("a").evaluate("el => el.href")
        h3 = result.query_selector("h3")
        if h3:
            title = h3.inner_text()
            result.query_selector("span").inner_text()
            s += f"\n{i+1}. {title} ({url})"
    return s


def _list_results_duckduckgo(page) -> str:
    # fetch the results
    results = page.query_selector(".react-results--main")
    results = results.query_selector_all("article")
    if not results:
        return "Error: something went wrong with the search."

    # list results
    s = "Results:"
    for i, result in enumerate(results):
        url = result.query_selector("a").evaluate("el => el.href")
        h2 = result.query_selector("h2")
        if h2:
            title = h2.inner_text()
            result.query_selector("span").inner_text()
            s += f"\n{i+1}. {title} ({url})"
    return s
