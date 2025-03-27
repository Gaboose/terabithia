from bs4 import BeautifulSoup
from typing import Dict, Any
import re

class DetailsError(Exception):
    """Details are not yet available."""

def parse_html_details(view_html: str) -> Dict[str, Any]:
    """Parse the HTML content and extract headers and nested `ul` elements into a dictionary."""
    soup = BeautifulSoup(view_html, "html.parser")
    details = {}

    def before(left, right):
        return (left.sourceline, left.sourcepos) < (right.sourceline, right.sourcepos)

    def parse_section(start_header):
        """Recursively parse headers and their associated content."""
        section_details = {}
        section = {start_header.get_text(strip=True): section_details}

        def before(left, right):
            return (left.sourceline, left.sourcepos) < (right.sourceline, right.sourcepos)

        next_header = start_header.find_next_sibling(lambda tag: tag.name and tag.name.startswith("h"))
        next_ul = start_header.find_next_sibling("ul")

        # Add ul to details, if it appears before the next header.
        if next_ul and (not next_header or before(next_ul, next_header)):
            for item in next_ul.find_all("li", class_="description_list__items"):
                key = item.find("div", class_="description_list__dt") or item.find("span", class_="description_list__dt")
                value = item.find("div", class_="description_list__dd") or item.find("span", class_="description_list__dd")
                if key and value:
                    section_details[re.sub(r'\s+', ' ', key.text.strip().strip(":"))] = re.sub(r'\s+', ' ', value.text.strip())
        
        # Find lower level headers.
        end_header = start_header.find_next_sibling(
            lambda tag: tag.name and tag.name.startswith("h") and tag.name <= start_header.name
        )
        cursor = start_header
        lower_level_headers = []
        while True:
            next_header = cursor.find_next_sibling(
                lambda tag: tag.name and tag.name.startswith("h") and tag.name > start_header.name
            )
            if not next_header or (end_header and not before(next_header, end_header)):
                break

            lower_level_headers.append(next_header)
            cursor = next_header

        # Keep only the top out of lower level headers.
        if lower_level_headers:
            min_header = min(lower_level_headers, key=lambda h: h.name)
            lower_level_headers = [h for h in lower_level_headers if h.name == min_header.name]

        # Parse recursively.
        for header in lower_level_headers:
            section_details.update(parse_section(header))

        return section

    # Find the top-level headers
    top_headers = soup.find_all(lambda tag: tag.name and tag.name.startswith("h"))
    if not top_headers:
        raise DetailsError('Details are not yet available')

    min_header = min(top_headers, key=lambda h: h.name)
    top_headers = [h for h in top_headers if h.name == min_header.name]

    for header in top_headers:
        details.update(parse_section(header))

    return details