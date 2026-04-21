from playwright.async_api import async_playwright
import asyncio
import sys
import os
import hashlib
import pathlib

playwright_dir = os.path.dirname(sys.executable)
browsers_path = os.path.join(playwright_dir, "ms-playwright")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path
print(f"Searching browsers in {browsers_path}")


class PreviewGenerator:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.current_page = None
        self.pending_task = None
        self.PREVIEW_CACHE_DIR = self.get_app_data_dir()

    def get_app_data_dir(self):
        # Preview folder in AppData/Roaming/AppName
        app_name = "Bookmark Curator"

        if os.name == 'nt':  # Windows
            base_dir = os.getenv('APPDATA')
        else:  # macOS/Linux
            base_dir = pathlib.Path.home() / ".local" / "share"

        data_dir = os.path.join(base_dir, app_name, "previews")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    async def init_browser(self):
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            print("Browser initialisation complete")

    async def close_browser(self):
        if self.browser:
            try:
                if self.current_page and not self.current_page.is_closed():
                    await self.current_page.close()
                await self.browser.close()
            except Exception as e:
                print(f"Error closing browser: {e}")
            finally:
                self.browser = None
                self.current_page = None
                print("Browser closed")

    async def get_screenshot(self, url: str, filename: str, save_path):
        page = None
        if not self.browser:
            await self.init_browser()
        if not self.browser:
            print("Browser not available. Skipping screenshot.")
            return

        try:
            ipad = self.playwright.devices['iPad Pro 11']    # 834x1194
            iphone = self.playwright.devices['iPhone 15 Pro Max']    # 430x932
            page = await self.browser.new_page(**iphone)

            print(f"New page opened for {url}")

            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
            except Exception as e:
                print(f"Error while loading {url}: {e}")

            if not page.is_closed():
                await page.screenshot(path=save_path)
                print(f"Screenshot saved: {filename, save_path}")

        except asyncio.CancelledError:
            print(f"Loading {url} canceled")
        except Exception as e:
            print(f"Error while loading {url}: {e}")
        finally:
            if page and not page.is_closed():
                try:
                    await page.close()
                    print(f"Page closed for {url}")
                except:
                    pass

            self.current_page = None

    async def get_cached_preview(self, url: str):
        # Generate unique filename based on link, put it in previews folder
        filename = hashlib.md5(url.encode()).hexdigest() + ".png"
        file_path = os.path.join(self.PREVIEW_CACHE_DIR, filename)

        try:
            if os.path.exists(file_path):
                print(f"Cache found: {filename}")
            else:
                print(f"Generating screenshot for {url}")
                await self.get_screenshot(url, filename, file_path)
        except Exception as e:
            print(e)

        return file_path