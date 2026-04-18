from dotenv import load_dotenv
import os

load_dotenv('.env',override=True)

class Config: 
    """
        Configuration class to load environment variables.
    """
    def __init__(self):
        if not os.getenv("BOT_TOKEN"):
            raise ValueError("BOT_TOKEN is not set in the environment variables.")
        else:
            self.BOT_TOKEN = os.getenv("BOT_TOKEN")

config = Config()