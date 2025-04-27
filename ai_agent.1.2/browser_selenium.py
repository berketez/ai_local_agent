# browser_selenium.py

"""
Browser Module - Handles browser automation using Selenium

This module provides platform-independent functionality to control web browsers
using the Selenium library and webdriver-manager.
"""

import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class SeleniumBrowserController:
    """Controls web browsers using Selenium."""

    def __init__(self, browser_type="chrome"):
        """Initialize the Selenium browser controller."""
        self.driver = None
        self.browser_type = browser_type.lower()
        self._initialize_driver()
        self.current_url = ""
        self.search_engines = {
            "google": "https://www.google.com/search?q={}",
            "bing": "https://www.bing.com/search?q={}",
            "duckduckgo": "https://duckduckgo.com/?q={}",
        }

    def _initialize_driver(self):
        """Initialize the Selenium WebDriver."""
        try:
            if self.browser_type == "chrome":
                options = webdriver.ChromeOptions()
                options.add_argument("--headless") # Run headless for server environment
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("window-size=1920x1080")
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            elif self.browser_type == "firefox":
                options = webdriver.FirefoxOptions()
                options.add_argument("--headless")
                service = FirefoxService(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=options)
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")
            print(f"Selenium WebDriver for {self.browser_type} initialized successfully.")
        except WebDriverException as e:
            print(f"Error initializing Selenium WebDriver for {self.browser_type}: {e}")
            # Fallback or further error handling can be added here
            self.driver = None
        except Exception as e:
            print(f"An unexpected error occurred during WebDriver initialization: {e}")
            self.driver = None

    def open_url(self, url: str) -> dict:
        """Open a URL in the browser."""
        if not self.driver:
            return {"success": False, "error": "WebDriver not initialized."}
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            
        try:
            self.driver.get(url)
            self.current_url = self.driver.current_url
            # Wait for page to load reasonably
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            return {"success": True, "current_url": self.current_url, "title": self.driver.title}
        except TimeoutException:
             return {"success": True, "current_url": self.current_url, "title": self.driver.title, "warning": "Page load timed out but navigation likely succeeded."}
        except WebDriverException as e:
            return {"success": False, "error": f"Error opening URL {url}: {e}"}

    def search_in_browser(self, query: str, search_engine: str = "google") -> dict:
        """Perform a search using a specified search engine."""
        engine = search_engine.lower()
        if engine not in self.search_engines:
            return {"success": False, "error": f"Unsupported search engine: {engine}. Supported: {list(self.search_engines.keys())}"}
            
        search_url = self.search_engines[engine].format(query.replace(' ', '+'))
        return self.open_url(search_url)

    def get_page_content(self, format="text") -> dict:
        """Get the content of the current page."""
        if not self.driver:
            return {"success": False, "error": "WebDriver not initialized."}
            
        try:
            if format == "html":
                content = self.driver.page_source
            elif format == "text":
                content = self.driver.find_element(By.TAG_NAME, 'body').text
            else:
                 return {"success": False, "error": f"Unsupported format: {format}. Supported: text, html"}
                 
            return {"success": True, "url": self.driver.current_url, "title": self.driver.title, "content": content}
        except NoSuchElementException:
            # If body tag is not found, maybe return page source as fallback?
             return {"success": False, "error": "Could not find body tag to extract text content."}
        except WebDriverException as e:
            return {"success": False, "error": f"Error getting page content: {e}"}

    def close_browser(self):
        """Close the browser and quit the WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                print("Browser closed successfully.")
            except WebDriverException as e:
                print(f"Error closing browser: {e}")
            finally:
                self.driver = None

# Example Usage (for testing)
if __name__ == '__main__':
    print("Testing SeleniumBrowserController...")
    # Try Chrome first, fallback to Firefox if needed
    browser_controller = None
    try:
        browser_controller = SeleniumBrowserController(browser_type="chrome")
        if not browser_controller.driver:
             raise WebDriverException("Chrome failed, trying Firefox")
    except Exception as e:
        print(f"Chrome initialization failed: {e}. Trying Firefox...")
        try:
            browser_controller = SeleniumBrowserController(browser_type="firefox")
            if not browser_controller.driver:
                 raise WebDriverException("Firefox also failed")
        except Exception as e_ff:
            print(f"Firefox initialization also failed: {e_ff}. Exiting.")
            exit(1)

    if browser_controller and browser_controller.driver:
        print("\nOpening Google...")
        result = browser_controller.open_url("https://www.google.com")
        print(result)

        if result["success"]:
            print("\nSearching for 'Python Selenium'...")
            search_result = browser_controller.search_in_browser("Python Selenium")
            print(search_result)

            if search_result["success"]:
                print("\nGetting page text content...")
                content_result = browser_controller.get_page_content(format="text")
                if content_result["success"]:
                    print(f"URL: {content_result['url']}")
                    print(f"Title: {content_result['title']}")
                    print(f"Content (first 500 chars):\n{content_result['content'][:500]}...")
                else:
                    print(f"Error getting content: {content_result['error']}")

        print("\nClosing browser...")
        browser_controller.close_browser()
    else:
        print("Failed to initialize any browser driver.")

