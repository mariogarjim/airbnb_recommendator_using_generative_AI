import os
import openai
import pandas as pd

from dotenv import load_dotenv

class AirbnbAssistant:
    """Airbnb assistant.

    Recommends airbnb to users.
    """

    def __init__(self) -> None:
        """Openai key must be replaced by your key"""
        
        self.response = None
        self.second_try = True

        # Load dotenv with your openai API key
        load_dotenv()
        openai.api_key = os.getenv("API_KEY")
    def chat_with_airbnb_assistant(self, airbnb_df, listings_detailed_df, user_query):
        """Recommends Airbnb listings based on a natural language user query.

        Parameters:
            airbnb_df (DataFrame): Dataframe with relevant information of avaliable airbnbs.
            listings_detailed_df (DataFrame): Detailed information of airbnbs.
            user_query (str): A natural language query from the user.            

        Returns:
            answer (string): A user-friendly recommendation generated by GPT based on the provided listings and query.
        """
        prompt = f"Here is the data of Airbnb listings:\n{airbnb_df}\n\nBased on this data, {user_query}"

        # Chat with GPT to generate the recommendation
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a travel assistant that provides Airbnb recommendations based on user preferences \
                            and available data. "
                        "For each user request, follow these steps:\n\n"
                        "1. **Identify Destination**: Analyze the user's input to determine the specific location \
                            they are interested in.\n"
                        "2. **Obtain Coordinates**: Find the latitude and longitude coordinates for this destination. "
                        "If coordinates are not available directly in the data, suggest a method to obtain them or \
                        estimate coordinates based on known landmarks near the destination \n"
                        "3. **Identify Travel Date**: Identify the date when the user want to travel. "
                        "If no date is specified, assume it is for the upcoming weekend.\n"
                        "4. **Determine number of travellers**: Identify the total number of travelers. "
                        "If unspecified, assume only one person is traveling\n"
                        "5.  **Set Maximum Price**: Determine the users maximum nightly budget. If no budget is specified, assume there is no maximum price.\n"
                        "6. **Validate Listings**: Select listings that are verified as available with an existing, valid id and meet the user's criteria for location, dates, travelers, and budget. "
                        "Use the `dates_prices` column for availability and pricing information.\n\n"
        
                        "7. Present each recommendation with '--', using '/' to separate components:\n"
                        "   '-- id / explanation for recommendation based on avaliable dates, coordinates, number of people and maximum price'\n"
                        "- **Example Format**:\n"
                        "   -- 123456 / I recommend it because ...\n"
                        "- **Formatting Notes**:\n"
                        "   - Start each recommendation with '--'.\n"
                        "   - Use '/' consistently to separate each component without spaces around it.\n"
                        "   - Include the id and a brief reason in each recommendation.\n\n"
                        "8. **Explain Each Recommendation**: For each recommended listing, provide a long explanation of why it is suitable. Try to be precise. "
                        "Focus on proximity to the destination, maximum price, and any other relevant criteria.\n\n"
                        "Make all recommendations clear, relevant, and personalized based on the user's request. Use a friendly tone."
                        "9. **Handle Missing or No Matches**: If no listings meet all criteria or you don't have a clear answer, reply with 'False'.\n\n"
        
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )

        raw_answer = response.choices[0].message.content
        print(f"Raw answer: {raw_answer}")
        print()

        is_valid, recommendation_result, reason_of_recommendation = self.valid_recommendation(
            answer=raw_answer, 
            listings_detailed=listings_detailed_df
            )
        if is_valid:
            airbnb_url, airbnb_image = self.get_airbnb_info(recommendation_result)
            self.response = {
                "recommendation": reason_of_recommendation,
                "url": airbnb_url,
                "image_url": airbnb_image
            }
        elif raw_answer == "False":
            self.response = {
                "recommendation": "Please provide more information!",
                "url": "",
                "image_url": ""
            }
        # If the answer is not in the correct format, try again asking to the LLM
        else:
            self.chat_with_airbnb_assistant(airbnb_df=airbnb_df, 
                                            user_query=user_query, 
                                            listings_detailed_df=listings_detailed_df)

        

    def get_airbnb_id_and_recommendation_from_response(self, text):
        """Get recommended airbnb id and reason of recommendation from response.

        Args:
            text (string): Chatgpt response

        Returns:
            airbnb_id (int), reason (string)
        """
        airbnb_id, reason = text.split("/")

        return int(airbnb_id.strip()), reason

    def valid_recommendation(self, answer, listings_detailed):
        """Return True if the recommendation is valid.
        - LLM response format is correct.
        - The recommended airbnb exists.

        Args:
            answer (string): LLM answer
            listings_detailed (DataFrame): Listing detailed dataframe 

        Returns:
            valid (boolean), recommended_airbnb (DataFrame), reason_of_recommendation (string)
        """
        valid = True
        answer_splitted_by_recommendation = answer.split("--")
        
        if len(answer_splitted_by_recommendation) == 1:
            valid = False
            return valid, pd.DataFrame(), ""
        
        first_recommendation = answer_splitted_by_recommendation[1]
        
        airbnb_id, *reason_of_recommendation = self.get_airbnb_id_and_recommendation_from_response(
            first_recommendation, 
        )
        if not reason_of_recommendation:
            valid = False
            return valid, pd.DataFrame(), ""
        
        recommended_airbnb = listings_detailed[listings_detailed["id"] == airbnb_id]
        if len(recommended_airbnb) == 0:
            valid = False
            return valid, pd.DataFrame(), ""
        
        return valid, recommended_airbnb, reason_of_recommendation
        

    def get_airbnb_info(self, recommended_airbnb):
        """Get airbnb relevant information from model answer

        Args:
            recommended_airbnb (DataFrame): Recommended airbnb by LLM

        Returns:
            airbnb_url (string), airbnb_image (string)
        """

        print(f"Recommendation: {recommended_airbnb}")
        airbnb_url = recommended_airbnb["listing_url"].iloc[0]
        airbnb_image = recommended_airbnb["picture_url"].iloc[0]

        return airbnb_url, airbnb_image