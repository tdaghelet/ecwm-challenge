"""
Scrapers pour récupérer les données des calendriers de courses
"""

from .ufolep_calendar import UfolepCalendarScraper, UfolepCalendarEntry

__all__ = ['UfolepCalendarScraper', 'UfolepCalendarEntry']
