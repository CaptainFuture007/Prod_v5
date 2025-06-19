"""
Academic Paper Search Module
Provides functionality to search for academic papers from various sources
"""

import requests
import time
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class PaperSearcher:
    """Base class for academic paper search"""
    
    def __init__(self, max_papers: int = 10, min_year: int = 2020):
        self.max_papers = max_papers
        self.min_year = min_year
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_papers(self, query: str) -> List[Dict[str, Any]]:
        """Search for papers based on query"""
        raise NotImplementedError
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s\-\.\,\(\)\[\]]', '', text)
        return text

class ArxivSearcher(PaperSearcher):
    """Search papers from ArXiv"""
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    def search_papers(self, query: str) -> List[Dict[str, Any]]:
        """Search ArXiv for papers"""
        papers = []
        
        try:
            # Build search query
            search_query = f"all:{query}"
            params = {
                'search_query': search_query,
                'start': 0,
                'max_results': self.max_papers,
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }
            
            logger.info(f"Searching ArXiv for: {query}")
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse XML response
            soup = BeautifulSoup(response.content, 'xml')
            entries = soup.find_all('entry')
            
            for entry in entries[:self.max_papers]:
                try:
                    # Extract basic information
                    title = self._clean_text(entry.find('title').text if entry.find('title') else "")
                    summary = self._clean_text(entry.find('summary').text if entry.find('summary') else "")
                    
                    # Extract authors
                    authors = []
                    for author in entry.find_all('author'):
                        name = author.find('name')
                        if name:
                            authors.append(self._clean_text(name.text))
                    
                    # Extract publication date
                    published = entry.find('published')
                    year = 2024  # Default
                    if published:
                        try:
                            year = int(published.text[:4])
                        except:
                            pass
                    
                    # Skip papers that are too old
                    if year < self.min_year:
                        continue
                    
                    # Extract PDF link
                    pdf_url = None
                    for link in entry.find_all('link'):
                        if link.get('type') == 'application/pdf':
                            pdf_url = link.get('href')
                            break
                    
                    if not pdf_url:
                        # Try to construct PDF URL from ID
                        id_elem = entry.find('id')
                        if id_elem:
                            arxiv_id = id_elem.text.split('/')[-1]
                            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                    
                    if title and pdf_url:
                        paper = {
                            'title': title,
                            'authors': authors,
                            'year': year,
                            'abstract': summary,
                            'pdf_url': pdf_url,
                            'source': 'ArXiv'
                        }
                        papers.append(paper)
                        logger.info(f"Found paper: {title[:50]}...")
                        
                except Exception as e:
                    logger.warning(f"Error parsing paper entry: {e}")
                    continue
            
            logger.info(f"Found {len(papers)} papers from ArXiv")
            
        except Exception as e:
            logger.error(f"Error searching ArXiv: {e}")
        
        return papers

class SemanticScholarSearcher(PaperSearcher):
    """Search papers from Semantic Scholar API"""
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    def search_papers(self, query: str) -> List[Dict[str, Any]]:
        """Search Semantic Scholar for papers"""
        papers = []
        
        try:
            params = {
                'query': query,
                'limit': self.max_papers,
                'fields': 'title,authors,year,abstract,openAccessPdf,url',
                'year': f"{self.min_year}-"
            }
            
            logger.info(f"Searching Semantic Scholar for: {query}")
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            for paper_data in data.get('data', [])[:self.max_papers]:
                try:
                    title = self._clean_text(paper_data.get('title', ''))
                    abstract = self._clean_text(paper_data.get('abstract', ''))
                    year = paper_data.get('year', 2024)
                    
                    # Extract authors
                    authors = []
                    for author in paper_data.get('authors', []):
                        if author.get('name'):
                            authors.append(self._clean_text(author['name']))
                    
                    # Get PDF URL
                    pdf_url = None
                    open_access = paper_data.get('openAccessPdf')
                    if open_access and open_access.get('url'):
                        pdf_url = open_access['url']
                    
                    if title and pdf_url and year >= self.min_year:
                        paper = {
                            'title': title,
                            'authors': authors,
                            'year': year,
                            'abstract': abstract,
                            'pdf_url': pdf_url,
                            'source': 'Semantic Scholar'
                        }
                        papers.append(paper)
                        logger.info(f"Found paper: {title[:50]}...")
                        
                except Exception as e:
                    logger.warning(f"Error parsing paper data: {e}")
                    continue
            
            logger.info(f"Found {len(papers)} papers from Semantic Scholar")
            
        except Exception as e:
            logger.error(f"Error searching Semantic Scholar: {e}")
        
        return papers

class MultiSourceSearcher:
    """Search papers from multiple sources"""
    
    def __init__(self, max_papers: int = 10, min_year: int = 2020):
        self.max_papers = max_papers
        self.min_year = min_year
        self.searchers = [
            ArxivSearcher(max_papers=max_papers//2, min_year=min_year),
            SemanticScholarSearcher(max_papers=max_papers//2, min_year=min_year)
        ]
    
    def search_papers(self, query: str) -> List[Dict[str, Any]]:
        """Search for papers from all sources"""
        all_papers = []
        
        for searcher in self.searchers:
            try:
                papers = searcher.search_papers(query)
                all_papers.extend(papers)
                time.sleep(1)  # Be respectful to APIs
            except Exception as e:
                logger.error(f"Error with {searcher.__class__.__name__}: {e}")
        
        # Remove duplicates based on title similarity
        unique_papers = self._remove_duplicates(all_papers)
        
        # Sort by year (newest first) and limit results
        unique_papers.sort(key=lambda x: x.get('year', 0), reverse=True)
        
        return unique_papers[:self.max_papers]
    
    def _remove_duplicates(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate papers based on title similarity"""
        unique_papers = []
        seen_titles = set()
        
        for paper in papers:
            title = paper.get('title', '').lower()
            # Create a simplified title for comparison
            simple_title = re.sub(r'[^\w\s]', '', title)
            simple_title = ' '.join(simple_title.split())
            
            if simple_title not in seen_titles:
                seen_titles.add(simple_title)
                unique_papers.append(paper)
        
        return unique_papers