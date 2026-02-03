import difflib

#Credit: Gemini assisted in code creation

class HeuristicMatcher:
    def __init__(self):  
        # keys backend uses
        self.standard_fields = {
            "first_name": ["first name", "given name", "fname", "first", "firstname"],
            "last_name": ["last name", "surname", "family name", "lname", "lastname"],
            "email": ["email", "e-mail address", "email address", "emailaddress"],
            "phone": ["phone", "mobile", "cell", "contact number", "phonenumber"],
            "resume": ["resume", "cv", "curriculum vitae", "upload resume"]
        }

    def get_best_match(self, element_metadata):
        """
        Determines which profile field matches the found web elements
        """
        # Combine all searchable texts from the element to make sure all labels are gathered
        search_blob = f"{element_metadata['label_text']} {element_metadata['placeholder']} {element_metadata['name']}".lower()

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

        # only return the key if confidence threshold is high enough
        return best_field if highest_score > 0.6 else "unknown"

#matcher = HeuristicMatcher()
#field_data = {"label_text": "Given Name", "placeholder": "Enter here", "name": "user_fname"}
#print(matcher.get_best_match(field_data)) # Should return "first_name"
