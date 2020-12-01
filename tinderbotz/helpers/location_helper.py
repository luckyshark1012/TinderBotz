from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import time


class LocationHelper:

    delay = 3

    HOME_URL = 'chrome-extension://cfohepagpmnodfdmjliccbbigdkfcgia/options.html#fixedPos'
    OPTIONS_URL = 'chrome-extension://cfohepagpmnodfdmjliccbbigdkfcgia/options.html'

    # Location options
    FIXED = 'fixed'
    REAL = 'real'
    # other location-options are: low, medium, high

    def __init__(self, browser):
        self.browser = browser
        self.initial_url = self.browser.current_url
        self.browser.get(self.HOME_URL)

    def setCustomLocation(self, location_name):
        # Time to load extension html
        time.sleep(2)

        # close overlay popup if presented
        try:
            xpath = '//*[@href="#close"]'
            self.browser.find_element_by_xpath(xpath).click()
        except:
            # overlay probably not shown
            pass

        # if this doesn't work, program should crash anyways, cuz something would needs fix
        xpath = '//*[@title="Search"]'
        element = self.browser.find_element_by_xpath(xpath)
        element.send_keys(location_name)
        element.send_keys(Keys.ENTER)

        try:
            xpath = '//*[@class="leaflet-pelias-list"]/li'
            WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located((By.XPATH, xpath)))
            element = self.browser.find_element_by_xpath(xpath)
            element.click()
        except TimeoutException:
            print("Setting custom Location failed.")
            print("Location Guard extension failed to access the internet to browse for custom location")
            print("Will use real location anyways. :/")
            return

        # Time to relocate map
        time.sleep(2)
        self.browser.find_element_by_xpath('//*[@id="fixedPosMap"]').click()

        # Make sure to use the city level
        self.setPrivacyLevel(self.FIXED)

        self.onEnd()

    def setRealtimeLocation(self):
        self.setPrivacyLevel(self.REAL)
        self.onEnd()

    def setPrivacyLevel(self, level):
        if self.browser.current_url != self.OPTIONS_URL:
            self.browser.get(self.OPTIONS_URL)
        # Time to load in extension html
        time.sleep(2)
        xpath = '//*[@id="defaultLevel"]/option'
        elements = self.browser.find_elements_by_xpath(xpath)
        for element in elements:
            if level in element.get_attribute('value'):
                element.click()
                break

    def onEnd(self):
        # check if restoring the session is needed
        if 'http' in self.initial_url:
            self.browser.get(self.initial_url)