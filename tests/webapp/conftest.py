"""
Pytest configuration for webapp tests.
"""
import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, base_url):
    """Configure browser context with base URL and other settings."""
    return {
        **browser_context_args,
        "base_url": base_url,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }


@pytest.fixture(scope="function")
def page(context, base_url):
    """Create a new page for each test with base URL configured."""
    page = context.new_page()
    page.goto(base_url)
    yield page
    page.close()