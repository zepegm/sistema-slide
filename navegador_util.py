from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementNotInteractableException

options = webdriver.ChromeOptions()
options.add_experimental_option("detach", True)
options.add_experimental_option('useAutomationExtension', False)
options.add_experimental_option('excludeSwitches', ['enable-automation'])
#options.add_argument("--start-fullscreen")
options.add_argument("--kiosk")

driver = webdriver.Chrome(options=options)



driver.get("http://localhost:120/slide")
driver.set_window_position(2000, 0)
driver.fullscreen_window()