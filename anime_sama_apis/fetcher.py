from typing import Literal
from DrissionPage import ChromiumOptions, WebPage
from requests import Response

class Fetcher:
    client: WebPage
    options: ChromiumOptions
    def __init__(
            self,
            domain: str,
            client: WebPage | None = None,
            options: ChromiumOptions | None = None
        ) -> None:
        if client:
            self.client = client
        else:
            if options:
                self.options = options
            else:
                self.options = ChromiumOptions()
                self.options.set_argument("--headless=new")
                self.options.headless(True)
                self.options.auto_port(True)
                self.options.set_argument("--blink-settings=imagesEnabled=false")
                # self.options.set_browser_path("/usr/bin/chromium")
                self.options.set_user_agent(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
                )
            self.client = WebPage(mode="d", chromium_options=self.options) # type: ignore
        self.client.get(domain)
        self.client.change_mode("s", go=False)
        self.client.quit() # Exit browser, we don't need it anymore, we have cookies.
    
    def get(self, url: str, retry: Literal[False] | None = None) -> Response:
        self.client.get(url, show_errmsg=False, retry=retry)
        return self.client.response
