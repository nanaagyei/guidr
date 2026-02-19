"""Fetch top schools from various ranking APIs and data sources."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from src.config import settings
from src.scrapers.base import BaseFetcher

logger = logging.getLogger(__name__)


@dataclass
class TopSchoolData:
    """Data for a top-ranked school."""
    name: str
    country: str
    city: Optional[str] = None
    website_url: Optional[str] = None
    qs_rank: Optional[int] = None
    the_rank: Optional[int] = None
    arwu_rank: Optional[int] = None
    usnews_rank: Optional[int] = None


class TopSchoolsFetcher(BaseFetcher):
    """
    Fetcher for top schools from various sources.
    
    Sources:
    - Wikipedia lists (free, reliable)
    - QS World Rankings (limited free access)
    - Times Higher Education (limited free access)
    - US News (US schools)
    """
    
    # Wikipedia list URLs
    WIKIPEDIA_SOURCES = [
        "https://en.wikipedia.org/wiki/QS_World_University_Rankings",
        "https://en.wikipedia.org/wiki/Times_Higher_Education_World_University_Rankings",
        "https://en.wikipedia.org/wiki/Academic_Ranking_of_World_Universities",
    ]
    
    # Manual list of top 100 world universities (reliable fallback)
    TOP_WORLD_UNIVERSITIES = [
        # USA
        ("Massachusetts Institute of Technology", "USA", "Cambridge"),
        ("Stanford University", "USA", "Stanford"),
        ("Harvard University", "USA", "Cambridge"),
        ("California Institute of Technology", "USA", "Pasadena"),
        ("University of Chicago", "USA", "Chicago"),
        ("University of Pennsylvania", "USA", "Philadelphia"),
        ("Yale University", "USA", "New Haven"),
        ("Columbia University", "USA", "New York"),
        ("Princeton University", "USA", "Princeton"),
        ("Cornell University", "USA", "Ithaca"),
        ("Duke University", "USA", "Durham"),
        ("Northwestern University", "USA", "Evanston"),
        ("Johns Hopkins University", "USA", "Baltimore"),
        ("University of California, Berkeley", "USA", "Berkeley"),
        ("University of California, Los Angeles", "USA", "Los Angeles"),
        ("University of Michigan", "USA", "Ann Arbor"),
        ("New York University", "USA", "New York"),
        ("Carnegie Mellon University", "USA", "Pittsburgh"),
        ("University of Washington", "USA", "Seattle"),
        ("University of Texas at Austin", "USA", "Austin"),
        ("Georgia Institute of Technology", "USA", "Atlanta"),
        ("University of Illinois Urbana-Champaign", "USA", "Champaign"),
        ("University of Wisconsin-Madison", "USA", "Madison"),
        ("University of California, San Diego", "USA", "San Diego"),
        ("University of Southern California", "USA", "Los Angeles"),
        ("Brown University", "USA", "Providence"),
        ("Rice University", "USA", "Houston"),
        ("Purdue University", "USA", "West Lafayette"),
        ("University of California, Davis", "USA", "Davis"),
        ("Boston University", "USA", "Boston"),
        
        # UK
        ("University of Oxford", "United Kingdom", "Oxford"),
        ("University of Cambridge", "United Kingdom", "Cambridge"),
        ("Imperial College London", "United Kingdom", "London"),
        ("University College London", "United Kingdom", "London"),
        ("University of Edinburgh", "United Kingdom", "Edinburgh"),
        ("University of Manchester", "United Kingdom", "Manchester"),
        ("King's College London", "United Kingdom", "London"),
        ("London School of Economics", "United Kingdom", "London"),
        
        # Canada
        ("University of Toronto", "Canada", "Toronto"),
        ("McGill University", "Canada", "Montreal"),
        ("University of British Columbia", "Canada", "Vancouver"),
        ("University of Waterloo", "Canada", "Waterloo"),
        ("University of Alberta", "Canada", "Edmonton"),
        ("McMaster University", "Canada", "Hamilton"),
        
        # Australia
        ("University of Melbourne", "Australia", "Melbourne"),
        ("University of Sydney", "Australia", "Sydney"),
        ("Australian National University", "Australia", "Canberra"),
        ("University of Queensland", "Australia", "Brisbane"),
        ("University of New South Wales", "Australia", "Sydney"),
        ("Monash University", "Australia", "Melbourne"),
        
        # Europe
        ("ETH Zurich", "Switzerland", "Zurich"),
        ("EPFL", "Switzerland", "Lausanne"),
        ("Technical University of Munich", "Germany", "Munich"),
        ("Ludwig Maximilian University of Munich", "Germany", "Munich"),
        ("Heidelberg University", "Germany", "Heidelberg"),
        ("University of Amsterdam", "Netherlands", "Amsterdam"),
        ("Delft University of Technology", "Netherlands", "Delft"),
        ("KU Leuven", "Belgium", "Leuven"),
        ("Sorbonne University", "France", "Paris"),
        ("PSL University", "France", "Paris"),
        
        # Asia
        ("National University of Singapore", "Singapore", "Singapore"),
        ("Nanyang Technological University", "Singapore", "Singapore"),
        ("Tsinghua University", "China", "Beijing"),
        ("Peking University", "China", "Beijing"),
        ("University of Hong Kong", "Hong Kong", "Hong Kong"),
        ("Hong Kong University of Science and Technology", "Hong Kong", "Hong Kong"),
        ("Chinese University of Hong Kong", "Hong Kong", "Hong Kong"),
        ("University of Tokyo", "Japan", "Tokyo"),
        ("Kyoto University", "Japan", "Kyoto"),
        ("Tokyo Institute of Technology", "Japan", "Tokyo"),
        ("Seoul National University", "South Korea", "Seoul"),
        ("KAIST", "South Korea", "Daejeon"),
        ("Indian Institute of Technology Bombay", "India", "Mumbai"),
        ("Indian Institute of Technology Delhi", "India", "New Delhi"),
        ("Indian Institute of Science", "India", "Bangalore"),
    ]
    
    # US News Top Graduate Schools (manually curated)
    US_TOP_GRAD_SCHOOLS = {
        "Computer Science": [
            "Carnegie Mellon University", "MIT", "Stanford University",
            "UC Berkeley", "University of Illinois Urbana-Champaign",
            "Cornell University", "University of Washington", "Georgia Tech",
            "Princeton University", "University of Texas at Austin",
        ],
        "Engineering": [
            "MIT", "Stanford University", "UC Berkeley",
            "California Institute of Technology", "Carnegie Mellon University",
            "Georgia Tech", "Purdue University", "University of Michigan",
            "University of Illinois Urbana-Champaign", "Cornell University",
        ],
        "Business": [
            "University of Pennsylvania (Wharton)", "Stanford University",
            "MIT (Sloan)", "Harvard Business School", "University of Chicago (Booth)",
            "Columbia Business School", "Northwestern (Kellogg)",
            "UC Berkeley (Haas)", "Yale School of Management", "Duke (Fuqua)",
        ],
        "Medicine": [
            "Harvard Medical School", "Johns Hopkins University",
            "Stanford University", "University of Pennsylvania",
            "Columbia University", "University of California, San Francisco",
            "Duke University", "Yale University", "University of Michigan",
            "Washington University in St. Louis",
        ],
        "Law": [
            "Yale Law School", "Stanford Law School", "Harvard Law School",
            "Columbia Law School", "University of Chicago Law School",
            "New York University School of Law", "University of Pennsylvania Law School",
            "University of Virginia School of Law", "UC Berkeley School of Law",
            "Duke University School of Law",
        ],
    }
    
    def __init__(self, timeout: int = 60):
        super().__init__(timeout=timeout)
    
    def fetch_all_top_schools(self) -> List[TopSchoolData]:
        """
        Fetch top schools from all available sources.
        
        Returns:
            List of TopSchoolData objects
        """
        schools: Dict[str, TopSchoolData] = {}
        
        # Start with curated list
        for i, (name, country, city) in enumerate(self.TOP_WORLD_UNIVERSITIES, 1):
            key = self._normalize_name(name)
            schools[key] = TopSchoolData(
                name=name,
                country=country,
                city=city,
                qs_rank=i if i <= 100 else None,  # Approximate rank
            )
        
        # Try to fetch from Wikipedia for more data
        try:
            wiki_schools = self._fetch_from_wikipedia()
            for school in wiki_schools:
                key = self._normalize_name(school.name)
                if key in schools:
                    # Update ranking info
                    if school.qs_rank:
                        schools[key].qs_rank = school.qs_rank
                    if school.the_rank:
                        schools[key].the_rank = school.the_rank
                else:
                    schools[key] = school
        except Exception as e:
            logger.warning(f"Failed to fetch from Wikipedia: {e}")
        
        return list(schools.values())
    
    def fetch_top_us_schools(self) -> List[TopSchoolData]:
        """Fetch top US schools specifically."""
        schools = []
        
        # Filter from world list
        for name, country, city in self.TOP_WORLD_UNIVERSITIES:
            if country == "USA":
                schools.append(TopSchoolData(
                    name=name,
                    country=country,
                    city=city,
                ))
        
        return schools
    
    def _fetch_from_wikipedia(self) -> List[TopSchoolData]:
        """
        Fetch school rankings from Wikipedia tables.
        
        Returns:
            List of schools with ranking data
        """
        schools = []
        
        for url in self.WIKIPEDIA_SOURCES[:1]:  # Just QS for now
            try:
                response = self._get_client().get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Find ranking tables
                tables = soup.find_all("table", class_="wikitable")
                
                for table in tables[:2]:  # First 2 tables usually have rankings
                    rows = table.find_all("tr")[1:]  # Skip header
                    
                    for row in rows[:100]:  # Top 100
                        cells = row.find_all(["td", "th"])
                        if len(cells) >= 2:
                            # Try to extract rank and name
                            rank_text = cells[0].get_text(strip=True)
                            name_text = cells[1].get_text(strip=True)
                            
                            rank = self._parse_rank(rank_text)
                            if rank and name_text:
                                schools.append(TopSchoolData(
                                    name=self._clean_name(name_text),
                                    country="Unknown",
                                    qs_rank=rank,
                                ))
            except Exception as e:
                logger.warning(f"Failed to parse {url}: {e}")
        
        return schools
    
    def _normalize_name(self, name: str) -> str:
        """Normalize school name for matching."""
        # Remove common suffixes and normalize
        name = name.lower()
        name = re.sub(r"\s*\(.*\)", "", name)  # Remove parentheticals
        name = re.sub(r"university of", "u", name)
        name = re.sub(r"[^a-z0-9]", "", name)
        return name
    
    def _clean_name(self, name: str) -> str:
        """Clean up school name from scraped data."""
        # Remove footnote markers
        name = re.sub(r"\[\d+\]", "", name)
        name = re.sub(r"\s+", " ", name)
        return name.strip()
    
    def _parse_rank(self, text: str) -> Optional[int]:
        """Parse rank from text."""
        # Handle ranges like "1-5" or single numbers
        match = re.search(r"(\d+)", text)
        if match:
            return int(match.group(1))
        return None
    
    def get_school_website(self, school_name: str) -> Optional[str]:
        """
        Try to find the official website for a school.
        
        Args:
            school_name: Name of the school
            
        Returns:
            Website URL or None
        """
        # Common domain patterns
        patterns = [
            (r"mit|massachusetts institute", "https://www.mit.edu"),
            (r"stanford", "https://www.stanford.edu"),
            (r"harvard", "https://www.harvard.edu"),
            (r"berkeley|uc berkeley", "https://www.berkeley.edu"),
            (r"oxford", "https://www.ox.ac.uk"),
            (r"cambridge", "https://www.cam.ac.uk"),
        ]
        
        name_lower = school_name.lower()
        for pattern, url in patterns:
            if re.search(pattern, name_lower):
                return url
        
        # Try to construct from name
        # e.g., "University of Michigan" -> "umich.edu"
        return None

