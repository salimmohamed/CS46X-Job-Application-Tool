from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os
import time
import encryption_service
import base64
from heuristic_matcher import HeuristicMatcher # import heuristic class 

# Credit to Gemini for assistance with writing

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


class FormInteractionEngine:
    def __init__(self, driver_path=None):
        self.driver = webdriver.Chrome()
        self.matcher = HeuristicMatcher()
        self.found_elements = []

    def getDecryptedData(self, encrypted_data):
        # decrypt the file so the values in users file can be correctly placed into form based on heuristic service
        try:
            decrypted_profile = encryption_service.decrypt_profile_simple(encrypted_data)
            return decrypted_profile
        except Exception as e:
            print(f"Failed to decrypt profile: {e}")
            return

    def load_test_page(self, file_path):
        """Loads local webpage testing framework"""
        abs_path = os.path.abspath(file_path)
        self.driver.get(f"file://{abs_path}")

    def get_fields(self):
        """Finds all elements in the page"""

        try:
            tags = ["input", "select", "textarea", "button"]

            # for each tag, find all the elements in the page for that tag and extract each elements data
            for tag in tags:
                elements = self.driver.find_elements(By.TAG_NAME, tag)
                for el in elements:
                    # extract metadata
                    self.found_elements.append({
                        "tag": tag,
                        "type": el.get_attribute("type") or "text",
                        "id": el.get_attribute("id"),
                        "name": el.get_attribute("name"),
                        "placeholder": el.get_attribute("placeholder"),
                        "label_text": self._find_label(el)
                    })
            return self.found_elements
        except Exception as e:
            return False

    def _find_label(self, element):
        """Finds the label of an element"""
        element_id = element.get_attribute("id")
        if element_id:
            try:
                label = self.driver.find_element(By.XPATH, f"//label[@for='{element_id}']")
                return label.text
            except:
                pass

        # fallback to check parent element text
        return element.find_element(By.XPATH, "..").text.split("\n")[0]

    def fill_form_from_profile(self, profile_data):

        results = []

        for element_metadata in self.found_elements:

            # fill the data on form where heuristic matcher says it should go
            backend_key = self.matcher.get_best_match(element_metadata)

            try:
                # get the user data that matches the key determined by heuristics matcher
                value_to_input = profile_data.get(backend_key)

                if value_to_input != None:
                    wait = WebDriverWait(self.driver, 10)
                    target_input = wait.until(EC.element_to_be_clickable(By.ID, element_metadata['id']))
                    target_input.clear()
                    target_input.send_keys(value_to_input)

                    results.append({"field": backend_key, "status": "SUCCESS"})

            except Exception as e:
                    results.append({"field": backend_key, "status": "FAILED", "error": str(e)})

        return results


    def save_logs(self, results, filename="interaction_log.json"):
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Logs from webdriver saved to: {filename}")


def main():
    engine = FormInteractionEngine()
    test_pages = []  # put test pages here!!!!!
    all_results = {} # make collection of results for all test pages

    try:
        # open the encrypted user file
        with open('profile.json', 'r') as f:
            encrypted_data = json.load(f)

        # decrypt the file
        decrypted_user_data = engine.getDecryptedData(encrypted_data)
        if not decrypted_user_data:
            print("ERROR: Could not decrypt data.\n")
            return

        for page in test_pages:
            print(f"Testing Page: {page}\n")
            engine.load_test_page(page)
            # clear the old elements before scanning the new page
            engine.found_elements = []
            # use the webdriver to get the fields that need to be filled
            engine.get_fields()
            # put that decrypted user data into the fields based on the matching field the heuristic matcher found
            page_results = engine.fill_form_from_profile(decrypted_user_data)
            all_results[page] = page_results
            time.sleep(2)

    except FileNotFoundError:
            print("Error: profile.json not found.")

    finally:
        # save results for testing
        engine.save_logs(all_results, "full_test_logs.json")
        engine.driver.quit()


if __name__ == "__main__":
    main()
