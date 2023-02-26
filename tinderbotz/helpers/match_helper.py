from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
import time

from tinderbotz.helpers.match import Match
from tinderbotz.helpers.constants_helper import Socials
from tinderbotz.helpers.loadingbar import LoadingBar
from tinderbotz.helpers.xpaths import content, modal_manager

class MatchHelper:

    delay = 5

    HOME_URL = "https://tinder.com/app/recs"

    def __init__(self, browser):
        self.browser = browser

    def _scroll_down(self, xpath):
        eula = self.browser.find_element(By.XPATH, xpath)
        self.browser.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', eula)

        SCROLL_PAUSE_TIME = 0.5

        # Get scroll height
        last_height = self.browser.execute_script("arguments[0].scrollHeight", eula)

        while True:
            # Scroll down to bottom
            self.browser.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", eula)

            # Wait to load page
            time.sleep(SCROLL_PAUSE_TIME)

            # Calculate new scroll height and compare with last scroll height
            new_height = self.browser.execute_script("arguments[0].scrollHeight", eula)
            if new_height == last_height:
                return True
            last_height = new_height


    def get_chat_ids(self, new, messaged):
        chatids = []

        xpath = '//button[@role="tab"]'
        try:
            WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located((By.XPATH, xpath)))
        except TimeoutException:
            print("match tab could not be found, trying again")
            self.browser.get(self.HOME_URL)
            time.sleep(1)
            return self.get_chat_ids(new, messaged)

        tabs = self.browser.find_elements(By.XPATH, xpath)

        if new:
            # Make sure we're in the 'new matches' tab
            for tab in tabs:
                if tab.text == 'Matches':
                    try:
                        tab.click()
                    except:
                        self.browser.get(self.HOME_URL)
                        return self.get_chat_ids(new, messaged)


            # start scraping new matches
            try:
                xpath = '//div[@role="tabpanel"]'

                # wait for element to appear
                WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located((By.XPATH, xpath)))

                div = self.browser.find_element(By.XPATH, xpath)

                list_refs = div.find_elements(By.XPATH, './/div/div/a')
                for index in range(len(list_refs)):
                    try:
                        ref = list_refs[index].get_attribute('href')
                        if "likes-you" in ref or "my-likes" in ref:
                            continue
                        else:
                            chatids.append(ref.split('/')[-1])
                    except:
                        continue

            except NoSuchElementException:
                pass

        if messaged:
            # Make sure we're in the 'messaged matches' tab
            for tab in tabs:
                if tab.text == 'Messages':
                    try:
                        tab.click()
                    except:
                        self.browser.get(self.HOME_URL)
                        return self.get_chat_ids(new, messaged)

            # Start scraping the chatted matches
            try:
                xpath = '//div[@class="messageList"]'

                # wait for element to appear
                WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(
                    (By.XPATH, xpath)))

                div = self.browser.find_element(By.XPATH, xpath)

                list_refs = div.find_elements(By.XPATH, './/a')
                for index in range(len(list_refs)):
                    try:
                        ref = list_refs[index].get_attribute('href')
                        chatids.append(ref.split('/')[-1])
                    except:
                        continue

            except NoSuchElementException:
                pass

        return chatids

    def get_new_matches(self, amount, quickload):
        matches = []
        used_chatids = []
        iteration = 0
        while True:
            iteration += 1
            if len(matches) >= amount:
                break

            new_chatids = self.get_chat_ids(new=True, messaged=False)
            copied = new_chatids.copy()
            for index in range(len(copied)):
                chatid = copied[index]
                if chatid in used_chatids:
                    new_chatids.remove(chatid)
                else:
                    used_chatids.append(chatid)

            # no new matches are found, MAX LIMIT
            if len(new_chatids) == 0:
                break

            # shorten the list so doesn't fetch ALL matches but just the amount it needs
            diff = len(matches) + len(new_chatids) - amount

            if diff > 0:
                del new_chatids[-diff:]

            print(f"\nGetting not-interacted-with, NEW MATCHES, part {iteration}")
            loadingbar = LoadingBar(len(new_chatids), "new matches")
            for index, chatid in enumerate(new_chatids):
                matches.append(self.get_match(chatid, quickload))
                loadingbar.update_loading(index)
            print("\n")

            # scroll down to get more chatids
            xpath = '//div[@role="tabpanel"]'
            tab = self.browser.find_element(By.XPATH, xpath)
            self.browser.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight;', tab)
            time.sleep(4)

        return matches

    def get_messaged_matches(self, amount, quickload):
        matches = []
        used_chatids = []
        iteration = 0
        while True:
            iteration += 1
            if len(matches) >= amount:
                break

            new_chatids = self.get_chat_ids(new=False, messaged=True)
            copied = new_chatids.copy()
            for index in range(len(copied)):
                if copied[index] in used_chatids:
                    new_chatids.remove(copied[index])
                else:
                    used_chatids.append(new_chatids[index])

            # no new matches are found, MAX LIMIT
            if len(new_chatids) == 0:
                break

            # shorten the list so doesn't fetch ALL matches but just the amount it needs
            diff = len(matches) + len(new_chatids) - amount
            if diff > 0:
                del new_chatids[-diff:]

            print(f"\nGetting interacted-with, MESSAGED MATCHES, part {iteration}")
            loadingbar = LoadingBar(len(new_chatids), "interacted-with-matches")
            for index, chatid in enumerate(new_chatids):
                matches.append(self.get_match(chatid, quickload))
                loadingbar.update_loading(index)
            print("\n")

            # scroll down to get more chatids
            xpath = '//div[@class="messageList"]'
            tab = self.browser.find_element(By.XPATH, xpath)
            self.browser.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight;', tab)
            time.sleep(4)

        return matches

    def send_message(self, chatid, message):
        if not self._is_chat_opened(chatid):
            self._open_chat(chatid)

        # locate the textbox and send message
        try:
            xpath = '//textarea'

            WebDriverWait(self.browser, self.delay).until(
                EC.presence_of_element_located((By.XPATH,xpath)))

            textbox = self.browser.find_element(By.XPATH, xpath)
            textbox.send_keys(message)
            textbox.send_keys(Keys.ENTER)

            print("Message sent succesfully.\nmessage: {}\n".format(message))

            # sleep so message can be sent
            time.sleep(1.5)
        except Exception as e:
            print("SOMETHING WENT WRONG LOCATING TEXTBOX")
            print(e)

    def send_gif(self, chatid, gifname):
        if not self._is_chat_opened(chatid):
            self._open_chat(chatid)

        try:
            xpath = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div[1]/div/div/div[3]/div/div[2]/button'

            WebDriverWait(self.browser, self.delay).until(
                EC.presence_of_element_located((By.XPATH, xpath)))
            gif_btn = self.browser.find_element(By.XPATH, xpath)

            gif_btn.click()
            time.sleep(1.5)

            search_box = self.browser.find_element(By.XPATH, '//textarea')
            search_box.send_keys(gifname)
            # give chance to load gif
            time.sleep(1.5)

            gif = self.browser.find_element(By.XPATH, '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div[1]/div/div/div[3]/div/div/div[1]/div[1]/div/div/div')
            gif.click()
            # sleep so gif can be sent
            time.sleep(1.5)

        except Exception as e:
            print(e)

    def send_song(self, chatid, songname):
        if not self._is_chat_opened(chatid):
            self._open_chat(chatid)

        try:
            xpath = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div[1]/div/div/div[4]/div/div[3]/button'

            WebDriverWait(self.browser, self.delay).until(
                EC.presence_of_element_located((By.XPATH, xpath)))
            song_btn = self.browser.find_element(By.XPATH, xpath)

            song_btn.click()
            time.sleep(1.5)

            search_box = self.browser.find_element(By.XPATH, '//textarea')
            search_box.send_keys(songname)
            # give chance to load gif
            time.sleep(1.5)

            song = self.browser.find_element(By.XPATH, 
                '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div[1]/div/div/div[3]/div/div[2]/div/div[1]/div[1]/div/div[1]/div/button')
            song.click()
            time.sleep(0.5)

            confirm_btn = self.browser.find_element(By.XPATH, '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div[1]/div/div/div[3]/div/div[2]/div/div[1]/div[2]/div/div[2]/button')
            confirm_btn.click()
            # sleep so song can be sent
            time.sleep(1.5)

        except Exception as e:
            print(e)

    def send_socials(self, chatid, media):
        did_match = False
        for social in (Socials):
            if social == media:
                did_match = True

        if not did_match: print("Media must be of type Socials"); return

        if not self._is_chat_opened(chatid):
            self._open_chat(chatid)

        try:
            xpath = f'{content}/div/div[1]/div/main/div[1]/div/div/div/div[1]/div/div/div[3]/div/div[1]/button'

            WebDriverWait(self.browser, self.delay).until(
                EC.presence_of_element_located((By.XPATH, xpath)))
            socials_btn = self.browser.find_element(By.XPATH, xpath)

            socials_btn.click()
            time.sleep(1)
            
            xpath = '//img[@alt="{}"]'.format(media.value)
            WebDriverWait(self.browser, self.delay).until(
                EC.presence_of_element_located((By.XPATH, xpath)))
            social_btn = self.browser.find_elements(By.XPATH, xpath)[-1]
            social_btn.click()

            # locate the sendbutton and send social
            try:
                self.browser.find_element(By.XPATH, "//button[@type='submit']").click()
                print("Succesfully send social card")
                # sleep so message can be sent
                time.sleep(1.5)
            except Exception as e:
                print("SOMETHING WENT WRONG LOCATING TEXTBOX")
                print(e)

        except Exception as e:
            print(e)
            self.browser.refresh()
            self.send_socials(chatid, media)

    def unmatch(self, chatid):
        if not self._is_chat_opened(chatid):
            self._open_chat(chatid)

        try:
            #'//button[text()="Unmatch"]'
            unmatch_button = self.browser.find_element(By.XPATH, f'{content}/div/div[1]/div/main/div[1]/div/div/div/div[2]/div/div[2]/div/button[1]')
            unmatch_button.click()
            time.sleep(1)


            unmatch_button = self.browser.find_element(By.XPATH, f'{modal_manager}/div/div/div[2]/button[1]')
            unmatch_button.click()
            time.sleep(1)

        except Exception as e:
            print("SOMETHING WENT WRONG FINDING THE UNMATCH BUTTONS")
            print(e)

    def _open_chat(self, chatid):
        if self._is_chat_opened(chatid): return;

        href = "/app/messages/{}".format(chatid)

        # look for the match with that chatid
        # first we're gonna look for the match in the already interacted matches
        try:
            xpath = '//*[@role="tab"]'
            # wait for element to appear
            WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located((By.XPATH, xpath)))

            tabs = self.browser.find_elements(By.XPATH, xpath)
            for tab in tabs:
                if tab.text == "Messages":
                    tab.click()
            time.sleep(1)
        except Exception as e:
            self.browser.get(self.HOME_URL)
            print(e)
            return self._open_chat(chatid)

        try:
            match_button = self.browser.find_element(By.XPATH, '//a[@href="{}"]'.format(href))
            self.browser.execute_script("arguments[0].click();", match_button)

        except Exception as e:
            # match reference not found, so let's see if match exists in the new not yet interacted matches
            xpath = '//*[@role="tab"]'
            # wait for element to appear
            WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located((By.XPATH, xpath)))

            tabs = self.browser.find_elements(By.XPATH, xpath)
            for tab in tabs:
                if tab.text == "Matches":
                    tab.click()

            time.sleep(1)

            try:
                matched_button = self.browser.find_element(By.XPATH, '//a[@href="{}"]'.format(href))
                matched_button.click()
            except Exception as e:
                # some kind of error happened, probably cuz chatid/ref/match doesnt exist (anymore)
                # Another error could be that the elements could not be found, cuz we're at a wrong url (potential bug)
                print(e)
        time.sleep(1)

    def get_match(self, chatid, quickload):
        if not self._is_chat_opened(chatid):
            self._open_chat(chatid)

        name = self.get_name(chatid)
        age = self.get_age(chatid)
        bio = self.get_bio(chatid)
        image_urls = self.get_image_urls(chatid, quickload)

        rowdata = self.get_row_data(chatid)
        work = rowdata.get('work')
        study = rowdata.get('study')
        home = rowdata.get('home')
        gender = rowdata.get('gender')
        distance = rowdata.get('distance')

        passions = self.get_passions(chatid)

        return Match(name=name, chatid=chatid, age=age, work=work, study=study, home=home, gender=gender, distance=distance, bio=bio, passions=passions, image_urls=image_urls)

    def get_name(self, chatid):
        if not self._is_chat_opened(chatid):
            self._open_chat(chatid)

        try:
            xpath = f'{content}/div/div[1]/div/main/div[1]/div/div/div/div[2]/div/div[1]/div/div/div[2]/div[1]/div/div[1]/div[1]/h1'
            element = self.browser.find_element(By.XPATH, xpath)
            WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located((By.XPATH, xpath)))
            return element.text
        except Exception as e:
            print(e)

    def get_age(self, chatid):
        if not self._is_chat_opened(chatid):
            self._open_chat(chatid)

        age = None

        try:
            xpath = f'{content}/div/div[1]/div/main/div[1]/div/div/div/div[2]/div/div[1]/div/div/div[2]/div[1]/div/div[1]/span'
            element = self.browser.find_element(By.XPATH, xpath)
            WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(
                (By.XPATH, xpath)))
            try:
               age = int(element.text)
            except ValueError:
                age = None
        except:
            pass

        return age


    _WORK_SVG_PATH = "M7.15 3.434h5.7V1.452a.728.728 0 0 0-.724-.732H7.874a.737.737 0 0 0-.725.732v1.982z"
    _STUDYING_SVG_PATH = "M11.87 5.026L2.186 9.242c-.25.116-.25.589 0 .705l.474.204v2.622a.78.78 0 0 0-.344.657c0 .42.313.767.69.767.378 0 .692-.348.692-.767a.78.78 0 0 0-.345-.657v-2.322l2.097.921a.42.42 0 0 0-.022.144v3.83c0 .45.27.801.626 1.101.358.302.842.572 1.428.804 1.172.46 2.755.776 4.516.776 1.763 0 3.346-.317 4.518-.777.586-.23 1.07-.501 1.428-.803.355-.3.626-.65.626-1.1v-3.83a.456.456 0 0 0-.022-.145l3.264-1.425c.25-.116.25-.59 0-.705L12.13 5.025c-.082-.046-.22-.017-.26 0v.001zm.13.767l8.743 3.804L12 13.392 3.257 9.599l8.742-3.806zm-5.88 5.865l5.75 2.502a.319.319 0 0 0 .26 0l5.75-2.502v3.687c0 .077-.087.262-.358.491-.372.29-.788.52-1.232.68-1.078.426-2.604.743-4.29.743s-3.212-.317-4.29-.742c-.444-.161-.86-.39-1.232-.68-.273-.23-.358-.415-.358-.492v-3.687z"
    _HOME_SVG_PATH = "M19.695 9.518H4.427V21.15h15.268V9.52zM3.109 9.482h17.933L12.06 3.709 3.11 9.482z"
    _LOCATION_SVG_PATH = "M11.436 21.17l-.185-.165a35.36 35.36 0 0 1-3.615-3.801C5.222 14.244 4 11.658 4 9.524 4 5.305 7.267 2 11.436 2c4.168 0 7.437 3.305 7.437 7.524 0 4.903-6.953 11.214-7.237 11.48l-.2.167zm0-18.683c-3.869 0-6.9 3.091-6.9 7.037 0 4.401 5.771 9.927 6.897 10.972 1.12-1.054 6.902-6.694 6.902-10.95.001-3.968-3.03-7.059-6.9-7.059h.001z"

    _WORK_SVG_PATH = "M7.15 3.434h5.7V1.452a.728.728 0 0 0-.724-.732H7.874a.737.737 0 0 0-.725.732v1.982z"
    _STUDYING_SVG_PATH = "M11.87 5.026L2.186 9.242c-.25.116-.25.589 0 .705l.474.204v2.622a.78.78 0 0 0-.344.657c0 .42.313.767.69.767.378 0 .692-.348.692-.767a.78.78 0 0 0-.345-.657v-2.322l2.097.921a.42.42 0 0 0-.022.144v3.83c0 .45.27.801.626 1.101.358.302.842.572 1.428.804 1.172.46 2.755.776 4.516.776 1.763 0 3.346-.317 4.518-.777.586-.23 1.07-.501 1.428-.803.355-.3.626-.65.626-1.1v-3.83a.456.456 0 0 0-.022-.145l3.264-1.425c.25-.116.25-.59 0-.705L12.13 5.025c-.082-.046-.22-.017-.26 0v.001zm.13.767l8.743 3.804L12 13.392 3.257 9.599l8.742-3.806zm-5.88 5.865l5.75 2.502a.319.319 0 0 0 .26 0l5.75-2.502v3.687c0 .077-.087.262-.358.491-.372.29-.788.52-1.232.68-1.078.426-2.604.743-4.29.743s-3.212-.317-4.29-.742c-.444-.161-.86-.39-1.232-.68-.273-.23-.358-.415-.358-.492v-3.687z"
    _HOME_SVG_PATH = "M19.695 9.518H4.427V21.15h15.268V9.52zM3.109 9.482h17.933L12.06 3.709 3.11 9.482z"
    _LOCATION_SVG_PATH = "M11.436 21.17l-.185-.165a35.36 35.36 0 0 1-3.615-3.801C5.222 14.244 4 11.658 4 9.524 4 5.305 7.267 2 11.436 2c4.168 0 7.437 3.305 7.437 7.524 0 4.903-6.953 11.214-7.237 11.48l-.2.167zm0-18.683c-3.869 0-6.9 3.091-6.9 7.037 0 4.401 5.771 9.927 6.897 10.972 1.12-1.054 6.902-6.694 6.902-10.95.001-3.968-3.03-7.059-6.9-7.059h.001z"
    _LOCATION_SVG_PATH_2 = "M11.445 12.5a2.945 2.945 0 0 1-2.721-1.855 3.04 3.04 0 0 1 .641-3.269 2.905 2.905 0 0 1 3.213-.645 3.003 3.003 0 0 1 1.813 2.776c-.006 1.653-1.322 2.991-2.946 2.993zm0-5.544c-1.378 0-2.496 1.139-2.498 2.542 0 1.404 1.115 2.544 2.495 2.546a2.52 2.52 0 0 0 2.502-2.535 2.527 2.527 0 0 0-2.499-2.545v-.008z"
    _GENDER_SVG_PATH = "M15.507 13.032c1.14-.952 1.862-2.656 1.862-5.592C17.37 4.436 14.9 2 11.855 2 8.81 2 6.34 4.436 6.34 7.44c0 3.07.786 4.8 2.02 5.726-2.586 1.768-5.054 4.62-4.18 6.204 1.88 3.406 14.28 3.606 15.726 0 .686-1.71-1.828-4.608-4.4-6.338"

    def get_row_data(self, chatid):
        if not self._is_chat_opened(chatid):
            self._open_chat(chatid)

        rowdata = {}

        xpath = '//div[@class="Row"]'
        rows = self.browser.find_elements(By.XPATH, xpath)

        for row in rows:
            svg = row.find_element(By.XPATH, ".//*[starts-with(@d, 'M')]").get_attribute('d')
            value = row.find_element(By.XPATH, ".//div[2]").text
            if svg == self._WORK_SVG_PATH:
                rowdata['work'] = value
            if svg == self._STUDYING_SVG_PATH:
                rowdata['study'] = value
            if svg == self._HOME_SVG_PATH:
                rowdata['home'] = value.split(' ')[-1]
            if svg == self._GENDER_SVG_PATH:
                rowdata['gender'] = value
            if svg == self._LOCATION_SVG_PATH or svg == self._LOCATION_SVG_PATH_2:
                distance = value.split(' ')[0]
                try:
                    distance = int(distance)
                except TypeError:
                    # Means the text has a value of 'Less than 1 km away'
                    distance = 1
                except ValueError:
                    distance = None

                rowdata['distance'] = distance

        return rowdata

    def get_passions(self, chatid):
        if not self._is_chat_opened(chatid):
            self._open_chat(chatid)

        passions = []
        xpath = f'{content}/div/div[1]/div/main/div[1]/div/div/div/div[2]/div/div[1]/div/div/div[2]/div/div/div[2]/div[2]/div'
        elements = self.browser.find_elements(By.XPATH, xpath)
        for el in elements:
            passions.append(el.text)

        return passions

    def get_bio(self, chatid):
        if not self._is_chat_opened(chatid):
            self._open_chat(chatid)

        try:
            xpath = f'{content}/div/div[1]/div/main/div[1]/div/div/div/div[2]/div/div[1]/div/div/div[2]/div[2]/div'
            return self.browser.find_element(By.XPATH, xpath).text
        except:
            # no bio included?
            return None

    def get_image_urls(self, chatid, quickload):
        try:
            if not self._is_chat_opened(chatid):
                self._open_chat(chatid)

            image_urls = []

            # only get url of first few images, and not click all bullets to get all image
            elements = self.browser.find_elements(By.XPATH, "//div[@aria-label='Profile slider']")
            for element in elements:
                image_url = element.value_of_css_property('background-image').split('\"')[1]
                if image_url not in image_urls:
                    image_urls.append(image_url)


            # return image urls without opening all images
            if quickload:
                return image_urls

            classname = 'bullet'
            # wait for element to appear
            WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(
                (By.CLASS_NAME, classname)))

            image_btns = self.browser.find_elements_by_class_name(classname)

            for btn in image_btns:
                btn.click()
                time.sleep(1)

                elements = self.browser.find_elements(By.XPATH, "//div[@aria-label='Profile slider']")
                for element in elements:
                    image_url = element.value_of_css_property('background-image').split('\"')[1]
                    if image_url not in image_urls:
                        image_urls.append(image_url)

        except StaleElementReferenceException:
            pass

        except TimeoutException:
            pass

        except Exception as e:
            print("unhandled exception getImageUrls in match_helper")
            print(e)

        return image_urls

    def _is_chat_opened(self, chatid):
        # open the correct user if not happened yet
        if chatid in self.browser.current_url:
            return True
        else:
            return False
