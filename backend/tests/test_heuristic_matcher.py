import difflib

#Credit: Gemini assisted in code creation

class HeuristicMatcher:
    def __init__(self):
        # keys backend uses
        self.standard_fields = {
            "first_name": ["first name", "given name", "fname", "first", "firstname"],
            "last_name": ["last name", "surname", "family name", "lname", "lastname"],
            "preferred_name": ["preferred name", "known as", "also known as"],
            "email": ["email", "e-mail address", "email address", "emailaddress"],
            "phone": ["phone", "mobile", "cell", "contact number", "phonenumber"],
            "address_line_1": ["address line 1", "street address", "address 1", "mailing address"],
            "address_line_2": ["address line 2", "address 2", "apt", "suite", "unit", "ste", "apartment", "building", "flat", "room", "floor", "bldg"],
            "resume": ["resume", "cv", "curriculum vitae", "upload resume"]
        }

    def get_best_match(self, element_metadata):
        """
        Determines which profile field matches the found web elements
        """

        label = element_metadata.get('label_text') or ""
        placeholder = element_metadata.get('placeholder') or ""
        name = element_metadata.get('name') or ""
        aria = element_metadata.get('aria_label') or ""

        # Combine all searchable texts from the element to make sure all labels are gathered
        # weighted search blob
        search_blob = f"{label} {aria} {placeholder} {name}".lower()

        best_field = None
        highest_score = 0.0

        # for each key in the backend key dictionary, check which key best matches the given element metadata 
        for standard_key, keywords in self.standard_fields.items():
            for word in keywords:
                # Calculate a similarity ratio 0.0 to 1.0
                score = difflib.SequenceMatcher(None, word, search_blob).ratio()

                # Boost score if the keyword is exactly inside the chunk
                if word in search_blob:
                    score += 0.5

                if score > highest_score:
                    highest_score = score
                    best_field = standard_key

        # stop address_line_1 from dominating all the location fills due to heuristic matching "address" with every address field
        if best_field == "address_line_1":
            # if supposed to be city:
            if "city" in search_blob:
                best_field = "city"
            # if supposed to be zip-code:
            if any(x in search_blob for x in ["zip-code", "zipcode", "zip", "postal"]):
                best_field = "zip_code"
            # if supposed to be address line 2
            if any(x in search_blob for x in ["address 2", "apt", "suite", "unit", "ste", "apartment"]):
                # overrule previous guess and make it actually address 2
                best_field = "address_line_2"
            # if address line 3 or higher, don't match
            if any(x in search_blob for x in ["line 3", "line 4", "line 5"]):
                best_field = "unknown"

        # only return the key if confidence threshold is high enough
        return best_field if highest_score > 0.6 else "unknown"

#matcher = HeuristicMatcher()
#field_data = {"label_text": "Given Name", "placeholder": "Enter here", "name": "user_fname"}
#print(matcher.get_best_match(field_data)) # Should return "first_name"
