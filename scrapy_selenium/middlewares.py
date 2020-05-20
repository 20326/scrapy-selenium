# -*- coding: utf-8 -*-
"""This module contains the ``SeleniumMiddleware`` scrapy middleware"""

from importlib import import_module

from scrapy import signals
from scrapy.exceptions import NotConfigured
from scrapy.http import HtmlResponse
from selenium.webdriver.support.ui import WebDriverWait

from .request import SeleniumRequest


class SeleniumMiddleware:
    """Scrapy middleware handling the requests using selenium"""

    def __init__(self, driver_name, driver_executable_path,
                 browser_executable_path, command_executor,
                 driver_arguments, desired_capabilities_arguments=None,
                 driver_use_wire=True, driver_wire_options=None,
                 driver_user_agent=None):
        """Initialize the selenium webdriver

        Parameters
        ----------
        driver_name: str
            The selenium ``WebDriver`` to use
        driver_executable_path: str
            The path of the executable binary of the driver
        driver_arguments: list
            A list of arguments to initialize the driver
        desired_capabilities_arguments: dict
            Dictionary object with non-browser specific
        driver_use_wire: bool
            Replace standard driver for requests, only support chrome, firefox, safari, Edge
        driver_use_wire: bool
            Replace standard driver for requests, only support chrome, firefox, safari, Edge
        driver_wire_options: dict
            Dictionary object with wire webdriver
        browser_executable_path: str
            The path of the executable binary of the browser
        command_executor: str
            Selenium remote server endpoint
        """

        webdriver_base_path = f'selenium.webdriver.{driver_name}'

        driver_klass_module = import_module(f'{webdriver_base_path}.webdriver')
        driver_klass = getattr(driver_klass_module, 'WebDriver')

        driver_options_module = import_module(f'{webdriver_base_path}.options')
        driver_options_klass = getattr(driver_options_module, 'Options')
        driver_options = driver_options_klass()

        if browser_executable_path:
            driver_options.binary_location = browser_executable_path

        for argument in driver_arguments:
            if argument.lower().startswith('user-agent'):
                if driver_user_agent:
                    argument = driver_user_agent
            driver_options.add_argument(argument)

        # set desired capabilities arguments: prefs, loggingPrefs ...
        if desired_capabilities_arguments:
            for (key, value) in desired_capabilities_arguments.items():
                driver_options.set_capability(key, value)

        # locally installed driver
        if driver_executable_path is not None:
            driver_kwargs = {
                'executable_path': driver_executable_path,
                f'{driver_name}_options': driver_options,
            }
            if driver_use_wire is True:
                # import selenium wire
                if driver_wire_options:
                    driver_kwargs['seleniumwire_options'] = driver_wire_options
                wire_driver_klass_module = import_module(f'seleniumwire.webdriver')
                wire_driver_klass = getattr(wire_driver_klass_module, driver_name.capitalize())
                self.driver = wire_driver_klass(**driver_kwargs)
            else:
                self.driver = driver_klass(**driver_kwargs)

            print('*' * 120, '\ndriver_kwargs: ', driver_options.capabilities, '\n', driver_wire_options, '\n', '*' * 120)
        # remote driver
        elif command_executor is not None:
            from selenium import webdriver
            capabilities = driver_options.to_capabilities()
            self.driver = webdriver.Remote(command_executor=command_executor,
                                           desired_capabilities=capabilities)

    @classmethod
    def from_crawler(cls, crawler):
        """Initialize the middleware with the crawler settings"""

        driver_name = crawler.settings.get('SELENIUM_DRIVER_NAME')
        driver_executable_path = crawler.settings.get('SELENIUM_DRIVER_EXECUTABLE_PATH')
        browser_executable_path = crawler.settings.get('SELENIUM_BROWSER_EXECUTABLE_PATH')
        command_executor = crawler.settings.get('SELENIUM_COMMAND_EXECUTOR')
        driver_arguments = crawler.settings.get('SELENIUM_DRIVER_ARGUMENTS')
        desired_capabilities = crawler.settings.get('SELENIUM_DRIVER_DESIRED_CAPABILITIES')
        driver_use_wire = crawler.settings.get('SELENIUM_DRIVER_USE_WIRE')
        driver_wire_options = crawler.settings.get('SELENIUM_DRIVER_WIRE_OPTIONS')
        driver_user_agent = crawler.settings.get('SELENIUM_DRIVER_USER_AGENT')

        if driver_name is None:
            raise NotConfigured('SELENIUM_DRIVER_NAME must be set')

        if driver_executable_path is None and command_executor is None:
            raise NotConfigured('Either SELENIUM_DRIVER_EXECUTABLE_PATH '
                                'or SELENIUM_COMMAND_EXECUTOR must be set')

        middleware = cls(
            driver_name=driver_name,
            driver_executable_path=driver_executable_path,
            browser_executable_path=browser_executable_path,
            command_executor=command_executor,
            driver_arguments=driver_arguments,
            desired_capabilities_arguments=desired_capabilities,
            driver_use_wire=driver_use_wire,
            driver_wire_options=driver_wire_options,
            driver_user_agent=driver_user_agent
        )

        crawler.signals.connect(middleware.spider_closed, signals.spider_closed)

        return middleware

    def process_request(self, request, spider):
        """Process a request using the selenium driver if applicable"""
        if isinstance(request, SeleniumRequest) is False:
            return None

        self.driver.get(request.url)
        for cookie_name, cookie_value in request.cookies.items():
            self.driver.add_cookie(
                {
                    'name': cookie_name,
                    'value': cookie_value
                }
            )

        if request.wait_until:
            WebDriverWait(self.driver, request.wait_time).until(
                request.wait_until
            )

        if request.screenshot:
            request.meta['screenshot'] = self.driver.get_screenshot_as_png()

        if request.script:
            self.driver.execute_script(request.script)

        body = str.encode(self.driver.page_source)

        # Expose the driver via the "meta" attribute
        request.meta.update({'driver': self.driver})

        return HtmlResponse(
            self.driver.current_url,
            body=body,
            encoding='utf-8',
            request=request
        )

    def spider_closed(self):
        """Shutdown the driver when spider is closed"""

        self.driver.quit()
