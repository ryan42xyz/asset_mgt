#!/usr/bin/env python3

import asyncio
import argparse
import sys
import os
from typing import List, Optional
from playwright.async_api import async_playwright
import html5lib
from multiprocessing import Pool
import time
from urllib.parse import urlparse
import logging
import getpass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

async def login_to_atlassian(page, email, password):
    """Login to Atlassian sites."""
    try:
        # Wait for the email input to appear and type the email
        await page.wait_for_selector('input[name="username"]', timeout=10000)
        await page.fill('input[name="username"]', email)
        
        # Click the continue button
        continue_button = await page.query_selector('button[type="submit"]')
        if continue_button:
            await continue_button.click()
            
        # Wait for the password input and type the password
        await page.wait_for_selector('input[name="password"]', timeout=10000)
        await page.fill('input[name="password"]', password)
        
        # Click the login button
        login_button = await page.query_selector('button[type="submit"]')
        if login_button:
            await login_button.click()
        
        # Wait for navigation to complete after login
        await page.wait_for_load_state('networkidle')
        
        # Check if we're redirected to a page that indicates successful login
        # This may need adjustment based on Atlassian's specific behavior
        current_url = page.url
        if 'login' not in current_url:
            logger.info("Login successful")
            return True
        else:
            logger.error("Login failed")
            return False
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        return False

async def fetch_page_with_login(url: str, context, email=None, password=None) -> Optional[str]:
    """Asynchronously fetch a webpage's content with login support."""
    page = await context.new_page()
    try:
        logger.info(f"Fetching {url}")
        await page.goto(url)
        
        # Check if we're on a login page for Atlassian
        if 'atlassian' in url and (await page.title()).lower().find('log in') >= 0:
            logger.info("Login page detected, attempting to login")
            if not email or not password:
                logger.error("Email and password required for login")
                return None
            
            login_success = await login_to_atlassian(page, email, password)
            if not login_success:
                return None
        
        # Wait for the page to fully load
        await page.wait_for_load_state('networkidle')
        
        # Take a screenshot for debugging (optional)
        await page.screenshot(path='page_after_login.png')
        
        content = await page.content()
        logger.info(f"Successfully fetched {url}")
        return content
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
        return None
    finally:
        await page.close()

def parse_html(html_content: Optional[str]) -> str:
    """Parse HTML content and extract text with hyperlinks in markdown format."""
    if not html_content:
        return ""
    
    try:
        document = html5lib.parse(html_content)
        result = []
        seen_texts = set()  # To avoid duplicates
        
        def should_skip_element(elem) -> bool:
            """Check if the element should be skipped."""
            # Skip script and style tags
            if elem.tag in ['{http://www.w3.org/1999/xhtml}script', 
                          '{http://www.w3.org/1999/xhtml}style']:
                return True
            # Skip empty elements or elements with only whitespace
            if not any(text.strip() for text in elem.itertext()):
                return True
            return False
        
        def process_element(elem, depth=0):
            """Process an element and its children recursively."""
            if should_skip_element(elem):
                return
            
            # Handle text content
            if hasattr(elem, 'text') and elem.text:
                text = elem.text.strip()
                if text and text not in seen_texts:
                    # Check if this is an anchor tag
                    if elem.tag == '{http://www.w3.org/1999/xhtml}a':
                        href = None
                        for attr, value in elem.items():
                            if attr.endswith('href'):
                                href = value
                                break
                        if href and not href.startswith(('#', 'javascript:')):
                            # Format as markdown link
                            link_text = f"[{text}]({href})"
                            result.append("  " * depth + link_text)
                            seen_texts.add(text)
                    else:
                        result.append("  " * depth + text)
                        seen_texts.add(text)
            
            # Process children
            for child in elem:
                process_element(child, depth + 1)
            
            # Handle tail text
            if hasattr(elem, 'tail') and elem.tail:
                tail = elem.tail.strip()
                if tail and tail not in seen_texts:
                    result.append("  " * depth + tail)
                    seen_texts.add(tail)
        
        # Start processing from the body tag
        body = document.find('.//{http://www.w3.org/1999/xhtml}body')
        if body is not None:
            process_element(body)
        else:
            # Fallback to processing the entire document
            process_element(document)
        
        # Filter out common unwanted patterns
        filtered_result = []
        for line in result:
            # Skip lines that are likely to be noise
            if any(pattern in line.lower() for pattern in [
                'var ', 
                'function()', 
                '.js',
                '.css',
                'google-analytics',
                'disqus',
                '{',
                '}'
            ]):
                continue
            filtered_result.append(line)
        
        return '\n'.join(filtered_result)
    except Exception as e:
        logger.error(f"Error parsing HTML: {str(e)}")
        return ""

async def process_urls_with_login(urls: List[str], email=None, password=None, max_concurrent: int = 2) -> List[str]:
    """Process multiple URLs concurrently with login capability."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            # Create browser contexts
            n_contexts = min(len(urls), max_concurrent)
            contexts = [await browser.new_context() for _ in range(n_contexts)]
            
            # Create tasks for each URL
            tasks = []
            for i, url in enumerate(urls):
                context = contexts[i % len(contexts)]
                task = fetch_page_with_login(url, context, email, password)
                tasks.append(task)
            
            # Gather results
            html_contents = await asyncio.gather(*tasks)
            
            # Parse HTML contents
            results = [parse_html(content) for content in html_contents]
            return results
            
        finally:
            # Cleanup
            for context in contexts:
                await context.close()
            await browser.close()

def validate_url(url: str) -> bool:
    """Validate if the given string is a valid URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def main():
    parser = argparse.ArgumentParser(description='Fetch and extract text content from webpages with login support.')
    parser.add_argument('urls', nargs='+', help='URLs to process')
    parser.add_argument('--email', help='Email for login')
    parser.add_argument('--max-concurrent', type=int, default=2,
                       help='Maximum number of concurrent browser instances (default: 2)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--no-headless', action='store_true',
                       help='Run browser in non-headless mode (visible)')
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Validate URLs
    valid_urls = []
    for url in args.urls:
        if validate_url(url):
            valid_urls.append(url)
        else:
            logger.error(f"Invalid URL: {url}")
    
    if not valid_urls:
        logger.error("No valid URLs provided")
        sys.exit(1)
    
    # Ask for login credentials if not provided
    email = args.email
    if not email and any('atlassian' in url for url in valid_urls):
        email = input("Enter your Atlassian email: ")
    
    password = None
    if email:
        password = getpass.getpass("Enter your password: ")
    
    start_time = time.time()
    try:
        results = asyncio.run(process_urls_with_login(valid_urls, email, password, args.max_concurrent))
        
        # Print results to stdout
        for url, text in zip(valid_urls, results):
            print(f"\n=== Content from {url} ===")
            print(text)
            print("=" * 80)
        
        logger.info(f"Total processing time: {time.time() - start_time:.2f}s")
        
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 