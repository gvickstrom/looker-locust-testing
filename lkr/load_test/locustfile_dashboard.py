from locust import User, between, task  # noqa
import os
from typing import List
import logging

import looker_sdk
from looker_sdk import models40
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from lkr.load_test.utils import (
    MAX_SESSION_LENGTH,
    PERMISSIONS,
    format_attributes,
    get_user_id,
)

__all__ = ["DashboardUser"]

# Set up logging
logger = logging.getLogger(__name__)


class DashboardUser(User):
    abstract = True
    wait_time = between(1000, 2000)
    # This should match your Looker instance's embed domain
    host = os.environ.get("LOOKERSDK_BASE_URL")
    abstract = True  # This is a base class

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sdk = None
        self.user_id = get_user_id()
        self.attributes: List[str] = []
        self.dashboard: str = ""
        self.models: List[str] = []
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Enhanced logging for user creation
        print(f"🚀 Creating new DashboardUser: {self.user_id}")
        if hasattr(self, 'processed_attributes') and self.processed_attributes:
            print(f"📋 User {self.user_id} assigned attributes: {self.processed_attributes}")
            self.attributes = self.processed_attributes
        else:
            print(f"⚠️  User {self.user_id} has no attributes assigned")

    def on_start(self):
        print(f"🔗 User {self.user_id} starting session...")
        print(f"📊 Dashboard: {self.dashboard}")
        print(f"🏗️  Models: {self.models}")
        
        # Initialize the SDK - make sure to set your environment variables
        self.sdk = looker_sdk.init40()
        attributes = format_attributes(self.attributes)
        
        print(f"🔑 User {self.user_id} formatted attributes: {attributes}")

        sso_url = self.sdk.create_sso_embed_url(
            models40.EmbedSsoParams(
                first_name="LoadTest",
                last_name=f"User-{self.user_id}",
                external_user_id=self.user_id,
                session_length=MAX_SESSION_LENGTH,  # max seconds
                target_url=f"{os.environ.get('LOOKERSDK_BASE_URL')}/embed/dashboards/{self.dashboard}",
                permissions=PERMISSIONS,
                models=self.models,
                user_attributes=attributes,
            )
        )

        print(f"🌐 User {self.user_id} opening dashboard at: {sso_url.url}")
        self.driver.get(sso_url.url)
        print(f"✅ User {self.user_id} successfully loaded dashboard")

    def on_stop(self):
        print(f"🛑 User {self.user_id} stopping session and closing browser")
        self.driver.quit()

    @task
    def do_nothing(self):
        # Add some logging to show the user is active
        print(f"💭 User {self.user_id} is active (doing nothing task)")
        pass