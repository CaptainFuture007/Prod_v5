"""
Minimal PDF Processing Pipeline - Streamlit Interface
Real PDF search and download functionality
"""

import streamlit as st
import logging
import sys
from pathlib import Path
from datetime import datetime
import time
from typing import Dict, Any, List
import threading

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.paper_search import MultiSourceSearcher, ArxivSearcher, SemanticScholarSearcher
from src.pdf_downloader import PDFDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="PDF Processing Pipeline v5",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def init_session_state():
    """Initialize session state variables"""
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'download_results' not in st.session_state:
        st.session_state.download_results = []
    if 'search_progress' not in st.session_state:
        st.session_state.search_progress = {'status': 'Not started', 'papers_found': 0}
    if 'download_progress' not in st.session_state:
        st.session_state.download_progress = {'status': 'Not started', 'completed': 0, 'total': 0}
    if 'processing' not in st.session_state:
        st.session_state.processing = False

def search_papers(query: str, max_papers: int, min_year: int, source: str):
    """Search for papers"""
    try:
        st.session_state.processing = True
        st.session_state.search_progress = {'status': 'Searching...', 'papers_found': 0}
        
        # Create searcher based on selected source
        if source == "ArXiv Only":
            searcher = ArxivSearcher(max_papers=max_papers, min_year=min_year)
        elif source == "Semantic Scholar Only":
            searcher = SemanticScholarSearcher(max_papers=max_papers, min_year=min_year)
        else:  # "All Sources"
            searcher = MultiSourceSearcher(max_papers=max_papers, min_year=min_year)
        
        logger.info(f"Starting search: '{query}' from {source}")
        papers = searcher.search_papers(query)
        
        st.session_state.search_results = papers
        st.session_state.search_progress = {
            'status': f'Found {len(papers)} papers',
            'papers_found': len(papers)
        }
        
        logger.info(f"Search completed: {len(papers)} papers found")
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        st.session_state.search_progress = {'status': f'Error: {str(e)}', 'papers_found': 0}
    finally:
        st.session_state.processing = False

def download_papers(papers: List[Dict[str, Any]], download_dir: str):
    """Download papers"""
    try:
        st.session_state.processing = True
        st.session_state.download_progress = {
            'status': 'Starting downloads...',
            'completed': 0,
            'total': len(papers)
        }
        
        downloader = PDFDownloader(download_dir=download_dir)
        
        def progress_callback(current, total, result):
            st.session_state.download_progress = {
                'status': f'Downloading {current}/{total}...',
                'completed': current,
                'total': total
            }
        
        logger.info(f"Starting downloads: {len(papers)} papers")
        results = downloader.download_papers(papers, progress_callback)
        
        st.session_state.download_results = results
        successful = sum(1 for r in results if r['success'])
        
        st.session_state.download_progress = {
            'status': f'Completed: {successful}/{len(papers)} successful',
            'completed': len(papers),
            'total': len(papers)
        }
        
        logger.info(f"Downloads completed: {successful}/{len(papers)} successful")
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        st.session_state.download_progress = {
            'status': f'Error: {str(e)}',
            'completed': 0,
            'total': 0
        }
    finally:
        st.session_state.processing = False

def render_search_interface():
    """Render the search interface"""
    st.header("🔍 Paper Search")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        query = st.text_input(
            "Search Query",
            placeholder="e.g., liquid biopsy, machine learning in healthcare",
            help="Enter keywords to search for academic papers"
        )
    
    with col2:
        max_papers = st.number_input(
            "Max Papers",
            min_value=1,
            max_value=50,
            value=10,
            help="Maximum number of papers to find"
        )
    
    with col3:
        min_year = st.number_input(
            "Min Year",
            min_value=2000,
            max_value=2025,
            value=2020,
            help="Minimum publication year"
        )
    
    # Source selection
    source = st.selectbox(
        "Search Source",
        ["All Sources", "ArXiv Only", "Semantic Scholar Only"],
        help="Choose which databases to search"
    )
    
    # Search button
    search_button = st.button(
        "🚀 Search Papers",
        disabled=st.session_state.processing or not query,
        type="primary"
    )
    
    if search_button and query:
        # Run search in a thread to avoid blocking UI
        thread = threading.Thread(
            target=search_papers,
            args=(query, max_papers, min_year, source)
        )
        thread.start()
        st.rerun()
    
    # Display search progress
    if st.session_state.search_progress['status'] != 'Not started':
        st.info(f"Search Status: {st.session_state.search_progress['status']}")
        
        if st.session_state.processing:
            st.spinner("Searching...")

def render_search_results():
    """Render search results"""
    if not st.session_state.search_results:
        return
    
    st.header("📋 Search Results")
    
    papers = st.session_state.search_results
    st.success(f"Found {len(papers)} papers")
    
    # Download settings
    col1, col2 = st.columns([1, 1])
    
    with col1:
        download_dir = st.text_input(
            "Download Directory",
            value="downloads",
            help="Directory to save PDF files"
        )
    
    with col2:
        st.write("")  # Spacer
        download_all = st.button(
            "📥 Download All PDFs",
            disabled=st.session_state.processing,
            type="primary"
        )
    
    if download_all:
        thread = threading.Thread(
            target=download_papers,
            args=(papers, download_dir)
        )
        thread.start()
        st.rerun()
    
    # Display download progress
    if st.session_state.download_progress['status'] != 'Not started':
        progress = st.session_state.download_progress
        if progress['total'] > 0:
            st.progress(progress['completed'] / progress['total'])
        st.info(f"Download Status: {progress['status']}")
    
    # Display papers table
    if papers:
        st.subheader("Papers Found")
        
        for i, paper in enumerate(papers):
            with st.expander(f"📄 {paper.get('title', 'Unknown Title')[:80]}..."):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Title:** {paper.get('title', 'N/A')}")
                    st.write(f"**Authors:** {', '.join(paper.get('authors', []))}")
                    st.write(f"**Year:** {paper.get('year', 'N/A')}")
                    st.write(f"**Source:** {paper.get('source', 'N/A')}")
                    
                    abstract = paper.get('abstract', '')
                    if abstract:
                        st.write(f"**Abstract:** {abstract[:300]}{'...' if len(abstract) > 300 else ''}")
                
                with col2:
                    pdf_url = paper.get('pdf_url', '')
                    if pdf_url:
                        st.link_button("🔗 View PDF", pdf_url)
                        
                        # Individual download button
                        if st.button(f"📥 Download", key=f"download_{i}"):
                            thread = threading.Thread(
                                target=download_papers,
                                args=([paper], download_dir)
                            )
                            thread.start()
                            st.rerun()

def render_download_results():
    """Render download results"""
    if not st.session_state.download_results:
        return
    
    st.header("📥 Download Results")
    
    results = st.session_state.download_results
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Downloads", len(results))
    with col2:
        st.metric("Successful", len(successful))
    with col3:
        st.metric("Failed", len(failed))
    
    # Show successful downloads
    if successful:
        st.subheader("✅ Successfully Downloaded")
        for result in successful:
            paper = result['paper']
            st.success(f"📄 {paper.get('title', 'Unknown')[:60]}...")
    
    # Show failed downloads
    if failed:
        st.subheader("❌ Failed Downloads")
        for result in failed:
            paper = result['paper']
            st.error(f"📄 {paper.get('title', 'Unknown')[:60]}... - {result['message']}")

def render_statistics():
    """Render download statistics"""
    try:
        downloader = PDFDownloader()
        stats = downloader.get_download_stats()
        
        if stats['total_files'] > 0:
            st.sidebar.header("📊 Download Stats")
            st.sidebar.metric("Total Files", stats['total_files'])
            st.sidebar.metric("Total Size", f"{stats['total_size_mb']} MB")
            
            with st.sidebar.expander("📁 Downloaded Files"):
                for filename in stats['files'][:10]:  # Show max 10 files
                    st.sidebar.text(f"📄 {filename}")
                if len(stats['files']) > 10:
                    st.sidebar.text(f"... and {len(stats['files']) - 10} more")
    
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")

def main():
    """Main application"""
    # Initialize session state
    init_session_state()
    
    # App header
    st.title("📄 PDF Processing Pipeline v5")
    st.markdown("**Real PDF Search and Download System**")
    st.markdown("Search academic papers from ArXiv and Semantic Scholar, then download PDFs automatically.")
    
    # Render main interface
    render_search_interface()
    
    # Auto-refresh during processing
    if st.session_state.processing:
        time.sleep(1)
        st.rerun()
    
    # Render results
    render_search_results()
    render_download_results()
    
    # Sidebar statistics
    render_statistics()
    
    # Footer
    st.markdown("---")
    st.markdown("💡 **Tips:** Use specific keywords for better results. Check download directory for saved PDFs.")

if __name__ == "__main__":
    main()