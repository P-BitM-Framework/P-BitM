# admin-backend/models/__init__.py

from database import Base

# User
from models.user import User
from models.user_session import UserSession

# Campaign & Victims
from models.campaign import Campaign, CampaignStatus
from models.victim import Victim, VictimStatus
from models.victim_event import VictimEvent, EventType
from models.captured_cookie import CapturedCookie

# Targets
from models.target import Target
from models.target_list import TargetList

# Email and SMTP
from models.email_template import EmailTemplate
from models.landing_page import LandingPage
from models.module import Module
from models.plugin import Plugin, PluginFile
from models.sending_profile import SMTPProfile

# Collected data
from models.data_collection import DataCollection

__all__ = [
    "Base",
    "User",
    "UserSession",
    "Campaign",
    "CampaignStatus",
    "Victim",
    "VictimStatus",
    "VictimEvent",
    "EventType",
    "CapturedCookie",
    "Target",
    "TargetList",
    "EmailTemplate",
    "SMTPProfile",
    "DataCollection",
    "LandingPage",
    "Module",
    "Plugin",
    "PluginFile"
]
