import aiohttp
import asyncio
import logging
import json
import os
from pymongo import MongoClient
from lxml import html
from datetime import datetime

# Configure logging
logging.basicConfig(filename='scraper.log', level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

# Load configuration from environment variables or a config file
MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'hackathons_db')
ENDPOINT_URL = os.getenv('ENDPOINT_URL', 'http://localhost:8000/api/hackathons')

# Initialize MongoDB client and database
client = MongoClient(MONGODB_URL)
db = client[DATABASE_NAME]
hackathons_collection = db['prev_hackathons']

async def fetch_hackathons(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                content = await response.text()

        doc = html.fromstring(content)
        
        # Extracting hackathons data
        hackathons = []
        hackathon_elements = doc.xpath('//div[@class="sc-xyzabc"]')  # Replace with the actual XPath
        
        for element in hackathon_elements:
            title = element.xpath('.//h3[@class="hackathon-title"]/text()')
            link = element.xpath('.//a[@class="hackathon-link"]/@href')
            mode = element.xpath('.//p[@class="hackathon-mode"]/text()')
            date = element.xpath('.//div[@class="hackathon-date"]/text()')
            
            if title and link and mode and date:
                hackathon_info = {
                    "title": title[0].strip(),
                    "link": link[0].strip(),
                    "mode": mode[0].strip(),
                    "Date": date[0].strip()
                }
                hackathons.append(hackathon_info)

        return hackathons

    except (aiohttp.ClientError, aiohttp.ClientConnectorError) as e:
        logging.error(f"Error fetching hackathons: {e}")

async def send_hackathons_to_endpoint(hackathons):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ENDPOINT_URL, json=hackathons) as response:
                response.raise_for_status()
                logging.info("Successfully sent new hackathons to the endpoint.")
    except aiohttp.ClientError as e:
        logging.error(f"Error sending hackathons to the endpoint: {e}")

def validate_hackathon_data(hackathon):
    # Implement data validation logic here
    # For example, you can check if certain fields are not empty or meet specific criteria
    if hackathon["title"] and hackathon["link"] and hackathon["mode"] and hackathon["Date"]:
        return True
    return False

async def main():
    logging.info("Running...")

    while True:
        try:
            hackathons = await fetch_hackathons('https://devfolio.co/hackathons')

            # Check for new hackathons and validate them
            new_hackathons = [hackathon for hackathon in hackathons if validate_hackathon_data(hackathon) and not hackathons_collection.find_one({"title": hackathon["title"]})]

            if new_hackathons:
                logging.info("New hackathons found:")
                for hackathon in new_hackathons:
                    pass
                logging.info(new_hackathons)

                # Send new hackathons to an endpoint asynchronously
                await send_hackathons_to_endpoint(new_hackathons)

                # Insert new hackathons into MongoDB
                hackathons_collection.insert_many(new_hackathons)

            else:
                logging.info("No new updates")

        except Exception as e:
            logging.error(f"Error: {e}")
            notice = {"title": "Bot Down", "link": "", "mode": "", "Date": datetime.now().isoformat()}
            try:
                await send_hackathons_to_endpoint(notice)
                logging.info("Successfully sent notice to the endpoint.")
            except aiohttp.ClientError as e:
                logging.error(f"Error sending notice to the endpoint: {e}")

        await asyncio.sleep(600)  # Sleep for 10 minutes (adjust as needed)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
