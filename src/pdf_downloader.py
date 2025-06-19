"""
PDF Download Module
Handles downloading of PDF files from various sources
"""

import requests
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import time
import hashlib
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)

class PDFDownloader:
    """Download PDF files from URLs"""
    
    def __init__(self, download_dir: str = "downloads", timeout: int = 30):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def download_paper(self, paper: Dict[str, Any]) -> Tuple[bool, Optional[Path], str]:
        """
        Download a single paper
        
        Returns:
            (success, file_path, message)
        """
        pdf_url = paper.get('pdf_url')
        title = paper.get('title', 'Unknown')
        
        if not pdf_url:
            return False, None, "No PDF URL provided"
        
        try:
            # Create safe filename
            safe_title = self._create_safe_filename(title)
            filename = f"{safe_title}.pdf"
            file_path = self.download_dir / filename
            
            # Check if file already exists
            if file_path.exists():
                logger.info(f"File already exists: {filename}")
                return True, file_path, f"Already exists: {filename}"
            
            logger.info(f"Downloading: {title[:50]}...")
            logger.info(f"URL: {pdf_url}")
            
            # Download the file
            response = self.session.get(pdf_url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Check if response contains PDF content
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not pdf_url.endswith('.pdf'):
                # Try to extract PDF URL from HTML if needed
                if 'text/html' in content_type:
                    pdf_url = self._extract_pdf_from_html(response.text, pdf_url)
                    if pdf_url:
                        response = self.session.get(pdf_url, timeout=self.timeout, stream=True)
                        response.raise_for_status()
                    else:
                        return False, None, "Could not find PDF link in HTML"
            
            # Save the file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Verify the downloaded file
            if file_path.stat().st_size < 1024:  # Less than 1KB is probably not a valid PDF
                file_path.unlink()  # Delete the file
                return False, None, "Downloaded file too small (probably not a PDF)"
            
            logger.info(f"Successfully downloaded: {filename}")
            return True, file_path, f"Downloaded: {filename}"
            
        except requests.exceptions.Timeout:
            return False, None, f"Timeout downloading: {title[:30]}..."
        except requests.exceptions.RequestException as e:
            return False, None, f"Download error: {str(e)[:50]}..."
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)[:50]}..."
    
    def download_papers(self, papers: List[Dict[str, Any]], 
                       progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        Download multiple papers
        
        Returns:
            List of download results with status information
        """
        results = []
        total_papers = len(papers)
        
        for i, paper in enumerate(papers):
            success, file_path, message = self.download_paper(paper)
            
            result = {
                'paper': paper,
                'success': success,
                'file_path': str(file_path) if file_path else None,
                'message': message,
                'index': i + 1,
                'total': total_papers
            }
            results.append(result)
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(i + 1, total_papers, result)
            
            # Add small delay between downloads to be respectful
            if i < total_papers - 1:
                time.sleep(1)
        
        return results
    
    def _create_safe_filename(self, title: str, max_length: int = 100) -> str:
        """Create a safe filename from paper title"""
        # Remove or replace problematic characters
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
        safe_title = re.sub(r'\s+', '_', safe_title.strip())
        
        # Limit length
        if len(safe_title) > max_length:
            safe_title = safe_title[:max_length]
        
        # Remove trailing periods and spaces
        safe_title = safe_title.rstrip('. ')
        
        # Ensure we have a valid filename
        if not safe_title:
            safe_title = f"paper_{int(time.time())}"
        
        return safe_title
    
    def _extract_pdf_from_html(self, html_content: str, base_url: str) -> Optional[str]:
        """Try to extract PDF URL from HTML content"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for PDF links
            pdf_patterns = [
                r'href=["\']([^"\']*.pdf[^"\']*)["\'']',
                r'src=["\']([^"\']*.pdf[^"\']*)["\'']',
            ]
            
            for pattern in pdf_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                if matches:
                    pdf_url = matches[0]
                    # Convert relative URLs to absolute
                    if not pdf_url.startswith('http'):
                        from urllib.parse import urljoin
                        pdf_url = urljoin(base_url, pdf_url)
                    return pdf_url
            
            # Look for meta tags or specific patterns for different sites
            meta_pdf = soup.find('meta', {'name': 'citation_pdf_url'})
            if meta_pdf and meta_pdf.get('content'):
                return meta_pdf['content']
            
        except Exception as e:
            logger.warning(f"Error extracting PDF from HTML: {e}")
        
        return None
    
    def get_download_stats(self) -> Dict[str, Any]:
        """Get statistics about downloaded files"""
        if not self.download_dir.exists():
            return {'total_files': 0, 'total_size': 0}
        
        pdf_files = list(self.download_dir.glob('*.pdf'))
        total_size = sum(f.stat().st_size for f in pdf_files)
        
        return {
            'total_files': len(pdf_files),
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'files': [f.name for f in pdf_files]
        }