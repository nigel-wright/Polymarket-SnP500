import requests
import json
import os
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY
from dotenv import load_dotenv
load_dotenv()

class PolymarketAPI:
    def __init__(self):
        self.gammaAPI = "https://gamma-api.polymarket.com/events"
        self.output_file = 'jsonOutputs/gamma_events.json'
        self.limit = 100  # Number of events per request
        self.clobAPI = "https://clob.polymarket.com"
        self.private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
        self.chain_id = 137  # Polygon Mainnet chain ID for eth layer 2 transactions 
        self.relevantInfo = []

    def get_and_save_all_events(self):
        all_events = []
        offset = 0

        while True:
            # Construct the URL with offset and limit
            url = f"{self.gammaAPI}?offset={offset}&limit={self.limit}&active=true&closed=false"
            response = requests.get(url)
            
            print(f"Fetching events starting at offset {offset}. Response status code: {response.status_code}")

            if response.status_code != 200:
                print(f"Error retrieving events at offset {offset}: {response.text}")
                break

            try:
                events = response.json()
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON at offset {offset}: {e}")
                print(f"Full response content: {response.text}")
                break

            # Ensure that the response is in the expected format (a list)
            if not isinstance(events, list):
                print(f"Unexpected response format at offset {offset}")
                break

            # Add the retrieved events to the list of all events
            all_events.extend(events)
            
            print(f"Retrieved {len(events)} events at offset {offset}")

            # If the number of events returned is less than the limit, we've hit the last page
            if len(events) < self.limit:
                break

            # Increment the offset to get the next batch of events
            offset += self.limit

        print(f"Total number of events retrieved: {len(all_events)}")

        # Save the events to a file
        if os.path.exists(self.output_file):
            os.remove(self.output_file)
            print(f"Deleted existing {self.output_file}")

        with open(self.output_file, 'w') as f:
            json.dump(all_events, f, indent=4)

        print(f"All Polymarket events have been saved to {self.output_file}")

    def generate_api_key(self):
        if not self.private_key:
            raise ValueError("Private key not found. Please set Polymarket_private_key in the .env file.")

        client = ClobClient(self.clobAPI, key=self.private_key, chain_id=self.chain_id)

        try:
            api_creds = client.create_or_derive_api_creds()
            print("API Key:", api_creds.api_key)
            print("Secret:", api_creds.api_secret)
            print("Passphrase:", api_creds.api_passphrase)

            # Save the credentials to the .env file
            with open('.env', 'a') as env_file:
                env_file.write(f"\nPolymarket_API_Key={api_creds.api_key}")
                env_file.write(f"\nPolymarket_API_Secret={api_creds.api_secret}")
                env_file.write(f"\nPolymarket_API_Passphrase={api_creds.api_passphrase}")

            print("API credentials have been saved to the .env file.")
        except Exception as e:
            print("Error creating or deriving API credentials:", e)
    
    def extract_event_and_markets_polymarket(self):
        with open(self.output_file, 'r') as f:
            events = json.load(f)

        event_with_markets = []
        for event in events:
            event_info = {
                "event_id": event.get("id"),
                "event_title": event.get("title", "No title provided"),
                "markets": []
            }

            for market in event.get("markets", []):
                market_info = {
                    "market_id": market.get("id"),
                    "question": market.get("question", "N/A"),
                    "description": market.get("description", "No description provided"),
                }
                event_info["markets"].append(market_info)
            
            event_with_markets.append(event_info)
        
        self.relevantInfo = event_with_markets
        return event_with_markets
    
    """ 
    Order types: FOK, GTC, GTD
    FOK: A 'Fill-Or-Kill' order is an market order to buy shares that must be executed immediately in its entirety; otherwise, the entire order will be cancelled.
    GTC: A 'Good-Til-Cancelled' order is a limit order that is active until it is fulfilled or cancelled.
    GTD: A 'Good-Til-Day' order is a type of order that is active until its specified date (UTC seconds timestamp), unless it has already been fulfilled or cancelled. 
        There is a security threshold of one minute: If the order needs to expire in 30 seconds the correct expiration value is: now + 1 miute + 30 seconds
    """
    def excecute_BUY_trade(self, price=0, size=0, side="BUY", token_id=""):
        if not self.private_key:
            raise ValueError("Private key not found. Please set POLYMARKET_PRIVATE_KEY in the .env file.")

        client = ClobClient(host=self.clobAPI, key=self.private_key, chain_id=self.chain_id)

        order_args = OrderArgs(
            price=price,
            size=size,
            side=side.upper(),
            token_id=token_id
        )

        signed_order = client.create_order(order_args)

        # Execute a GTC (Good-Til-Cancelled) order
        try:
            resp = client.post_order(signed_order, OrderType.GTC)
            print("Order Response:", resp)
        except Exception as e:
            print("Error executing the trade:", e)


if __name__ == "__main__":
    polymarket_api = PolymarketAPI()
    # polymarket_api.get_and_save_all_events()
    # polymarket_api.generate_api_key()
    print(polymarket_api.excecute_BUY_trade(price=0.9, size=10, token_id="111175715817805901423788267072432098012720878920613639403125493701679912829791"))
    # print(json.dumps(polymarket_api.extract_event_and_markets_polymarket(), indent=4))
