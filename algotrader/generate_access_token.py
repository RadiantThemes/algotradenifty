# algotrader/generate_access_token.py

import logging
from kiteconnect import KiteConnect
import settings

# Configure logging
logging.basicConfig(level=logging.INFO)

def generate_token():
    """
    Guides the user through the process of generating a Kite Connect access token.
    """
    if settings.API_KEY == "YOUR_API_KEY" or settings.API_SECRET == "YOUR_API_SECRET":
        logging.error("API_KEY or API_SECRET is not set in settings.py. Please update it.")
        return

    try:
        # Initialize KiteConnect client
        kite = KiteConnect(api_key=settings.API_KEY)

        # Generate the login URL
        login_url = kite.login_url()
        print("-" * 50)
        print("Step 1: Open the following URL in your browser and log in:")
        print(login_url)
        print("-" * 50)

        # Prompt the user to enter the request token
        request_token = input("Step 2: After logging in, you will be redirected. \n"
                              "Copy the 'request_token' from the URL and paste it here: ")

        if not request_token:
            logging.error("Request token cannot be empty.")
            return

        # Generate the session (access token)
        logging.info("Generating session with the provided request token...")
        session = kite.generate_session(request_token.strip(), api_secret=settings.API_SECRET)

        access_token = session.get("access_token")

        if not access_token:
            logging.error("Failed to generate access token. Response: %s", session)
            return

        print("\n" + "=" * 50)
        print("SUCCESS! Your access token has been generated.")
        print(f"Access Token: {access_token}")
        print("\nStep 3: Copy this access token and paste it into your settings.py file")
        print("         for the 'ACCESS_TOKEN' variable.")
        print("=" * 50)

    except Exception as e:
        logging.error(f"An error occurred during token generation: {e}")

if __name__ == "__main__":
    generate_token()
