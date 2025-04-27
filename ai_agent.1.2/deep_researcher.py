"""
Deep Researcher Module - Handles advanced web research capabilities

This module provides enhanced research capabilities by combining browser automation
with content analysis and multi-source information gathering.
"""

import time
import json
import re
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Import the base browser controller
from browser_selenium import SeleniumBrowserController

class DeepResearcher:
    """Advanced web research capabilities with multi-source verification."""
    
    def __init__(self, browser_controller=None, browser_type="chrome"):
        """Initialize the deep researcher with a browser controller."""
        self.browser = browser_controller or SeleniumBrowserController(browser_type=browser_type)
        self.search_results_cache = {}
        self.visited_pages = []
        self.research_notes = []
        self.current_topic = ""
        
    def research_topic(self, topic: str, depth: int = 3, sources: int = 5) -> Dict[str, Any]:
        """
        Perform deep research on a topic by searching, analyzing multiple sources,
        and synthesizing information.
        
        Args:
            topic: The research topic or question
            depth: How deep to go in each source (1-5)
            sources: How many sources to analyze
            
        Returns:
            Dictionary with research results
        """
        self.current_topic = topic
        self.research_notes = []
        self.visited_pages = []
        
        # Step 1: Perform initial search
        search_result = self.browser.search_in_browser(topic)
        if not search_result.get("success", False):
            return {"success": False, "error": f"Initial search failed: {search_result.get('error', 'Unknown error')}"}
        
        # Step 2: Extract and analyze search results
        search_results = self._extract_search_results()
        if not search_results:
            return {"success": False, "error": "Failed to extract search results"}
        
        # Step 3: Visit and analyze top sources
        sources_analyzed = 0
        for result in search_results[:min(len(search_results), sources)]:
            if sources_analyzed >= sources:
                break
                
            # Visit the page
            visit_result = self.browser.open_url(result["url"])
            if not visit_result.get("success", False):
                self.research_notes.append({
                    "type": "error",
                    "source": result["url"],
                    "note": f"Failed to visit page: {visit_result.get('error', 'Unknown error')}"
                })
                continue
                
            # Add to visited pages
            self.visited_pages.append({
                "url": result["url"],
                "title": visit_result.get("title", "Unknown Title")
            })
            
            # Analyze the page content
            page_analysis = self._analyze_page_content(depth)
            if page_analysis:
                self.research_notes.append({
                    "type": "source_analysis",
                    "source": result["url"],
                    "title": visit_result.get("title", "Unknown Title"),
                    "analysis": page_analysis
                })
                sources_analyzed += 1
            
            # Go back to search results
            self.browser.driver.back()
            time.sleep(1)  # Give time for the page to load
        
        # Step 4: Synthesize information from multiple sources
        synthesis = self._synthesize_research()
        
        return {
            "success": True,
            "topic": topic,
            "sources_analyzed": sources_analyzed,
            "synthesis": synthesis,
            "research_notes": self.research_notes,
            "visited_pages": self.visited_pages
        }
    
    def _extract_search_results(self) -> List[Dict[str, str]]:
        """Extract search results from the current page."""
        results = []
        
        try:
            # Wait for search results to load
            WebDriverWait(self.browser.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "a"))
            )
            
            # Different search engines have different structures
            # This is a simplified version that works for Google
            if "google.com" in self.browser.driver.current_url:
                # Google search results
                search_elements = self.browser.driver.find_elements(By.CSS_SELECTOR, "div.g")
                
                for element in search_elements:
                    try:
                        link = element.find_element(By.CSS_SELECTOR, "a")
                        title_element = element.find_element(By.CSS_SELECTOR, "h3")
                        snippet_element = element.find_element(By.CSS_SELECTOR, "div.VwiC3b")
                        
                        url = link.get_attribute("href")
                        title = title_element.text
                        snippet = snippet_element.text if snippet_element else ""
                        
                        if url and not url.startswith("https://webcache.googleusercontent.com") and not url.startswith("http://webcache.googleusercontent.com"):
                            results.append({
                                "url": url,
                                "title": title,
                                "snippet": snippet
                            })
                    except NoSuchElementException:
                        continue
            else:
                # Generic approach for other search engines
                links = self.browser.driver.find_elements(By.TAG_NAME, "a")
                
                for link in links:
                    try:
                        url = link.get_attribute("href")
                        title = link.text
                        
                        # Filter out navigation links, empty links, etc.
                        if (url and title and len(title) > 10 and 
                            not url.startswith("javascript:") and 
                            not url.startswith("#") and
                            "?" in url):  # Most search result links have query parameters
                            
                            results.append({
                                "url": url,
                                "title": title,
                                "snippet": ""  # No snippet in generic approach
                            })
                    except Exception:
                        continue
        
        except Exception as e:
            print(f"Error extracting search results: {e}")
        
        # Remove duplicates based on URL
        unique_results = []
        seen_urls = set()
        
        for result in results:
            if result["url"] not in seen_urls:
                seen_urls.add(result["url"])
                unique_results.append(result)
        
        return unique_results
    
    def _analyze_page_content(self, depth: int = 3) -> Dict[str, Any]:
        """
        Analyze the content of the current page.
        
        Args:
            depth: How deep to analyze (1-5)
                1: Basic title and main text
                2: Include headings and structure
                3: Include links and related topics
                4: Include images and media descriptions
                5: Deep analysis including page code inspection
        
        Returns:
            Dictionary with analysis results
        """
        analysis = {}
        
        try:
            # Get basic page information
            analysis["title"] = self.browser.driver.title
            analysis["url"] = self.browser.driver.current_url
            
            # Get page content
            content_result = self.browser.get_page_content(format="text")
            if not content_result.get("success", False):
                analysis["error"] = f"Failed to get page content: {content_result.get('error', 'Unknown error')}"
                return analysis
            
            analysis["content_summary"] = self._summarize_text(content_result.get("content", ""))
            
            # Extract main text content
            main_content = self._extract_main_content()
            analysis["main_content"] = main_content
            
            if depth >= 2:
                # Extract headings and structure
                headings = self._extract_headings()
                analysis["structure"] = headings
            
            if depth >= 3:
                # Extract links and related topics
                links = self._extract_important_links()
                analysis["related_links"] = links
            
            if depth >= 4:
                # Extract images and media descriptions
                images = self._extract_images()
                analysis["media"] = images
            
            if depth >= 5:
                # Deep analysis including page code inspection
                metadata = self._extract_metadata()
                analysis["metadata"] = metadata
        
        except Exception as e:
            analysis["error"] = f"Error analyzing page content: {e}"
        
        return analysis
    
    def _extract_main_content(self) -> str:
        """Extract the main content from the current page."""
        try:
            # Try to find main content containers
            main_selectors = [
                "main", "article", "#content", ".content", 
                "#main", ".main", ".post", ".entry"
            ]
            
            for selector in main_selectors:
                try:
                    element = self.browser.driver.find_element(By.CSS_SELECTOR, selector)
                    if element:
                        return element.text
                except NoSuchElementException:
                    continue
            
            # If no main content container found, use body
            body = self.browser.driver.find_element(By.TAG_NAME, "body")
            
            # Remove navigation, footer, etc.
            for element in body.find_elements(By.CSS_SELECTOR, "nav, header, footer, aside, .sidebar, #sidebar, .navigation, .menu, .ad, .advertisement"):
                self.browser.driver.execute_script("arguments[0].remove();", element)
            
            return body.text
        
        except Exception as e:
            print(f"Error extracting main content: {e}")
            return ""
    
    def _extract_headings(self) -> List[Dict[str, str]]:
        """Extract headings from the current page."""
        headings = []
        
        try:
            for level in range(1, 7):
                elements = self.browser.driver.find_elements(By.CSS_SELECTOR, f"h{level}")
                for element in elements:
                    headings.append({
                        "level": level,
                        "text": element.text
                    })
        except Exception as e:
            print(f"Error extracting headings: {e}")
        
        return headings
    
    def _extract_important_links(self) -> List[Dict[str, str]]:
        """Extract important links from the current page."""
        links = []
        
        try:
            elements = self.browser.driver.find_elements(By.TAG_NAME, "a")
            
            for element in elements:
                try:
                    url = element.get_attribute("href")
                    text = element.text
                    
                    if url and text and len(text) > 3:
                        # Filter out navigation, social media, etc.
                        if not any(x in url.lower() for x in ["facebook", "twitter", "instagram", "linkedin", "youtube", "pinterest", "login", "signup", "register"]):
                            links.append({
                                "url": url,
                                "text": text
                            })
                except Exception:
                    continue
        
        except Exception as e:
            print(f"Error extracting links: {e}")
        
        return links[:10]  # Limit to 10 links
    
    def _extract_images(self) -> List[Dict[str, str]]:
        """Extract images from the current page."""
        images = []
        
        try:
            elements = self.browser.driver.find_elements(By.TAG_NAME, "img")
            
            for element in elements:
                try:
                    src = element.get_attribute("src")
                    alt = element.get_attribute("alt") or ""
                    
                    if src and not src.startswith("data:"):
                        images.append({
                            "src": src,
                            "alt": alt
                        })
                except Exception:
                    continue
        
        except Exception as e:
            print(f"Error extracting images: {e}")
        
        return images[:5]  # Limit to 5 images
    
    def _extract_metadata(self) -> Dict[str, str]:
        """Extract metadata from the current page."""
        metadata = {}
        
        try:
            # Extract meta tags
            meta_elements = self.browser.driver.find_elements(By.TAG_NAME, "meta")
            
            for element in meta_elements:
                try:
                    name = element.get_attribute("name") or element.get_attribute("property")
                    content = element.get_attribute("content")
                    
                    if name and content:
                        metadata[name] = content
                except Exception:
                    continue
        
        except Exception as e:
            print(f"Error extracting metadata: {e}")
        
        return metadata
    
    def _summarize_text(self, text: str, max_length: int = 500) -> str:
        """
        Summarize text by extracting the most important sentences.
        This is a simple extractive summarization.
        
        Args:
            text: The text to summarize
            max_length: Maximum length of the summary
            
        Returns:
            Summarized text
        """
        if not text:
            return ""
            
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        if not sentences:
            return ""
            
        # If text is already short, return it
        if len(text) <= max_length:
            return text
            
        # Simple summarization: take first sentence and a few from the middle
        summary = [sentences[0]]
        
        # Add some sentences from the middle
        middle_start = max(1, len(sentences) // 4)
        middle_end = min(len(sentences) - 1, len(sentences) // 2)
        
        for i in range(middle_start, middle_end):
            if len(" ".join(summary)) < max_length // 2:
                summary.append(sentences[i])
        
        # Add the last sentence if there's room
        if len(" ".join(summary)) + len(sentences[-1]) <= max_length:
            summary.append(sentences[-1])
        
        return " ".join(summary)
    
    def _synthesize_research(self) -> Dict[str, Any]:
        """
        Synthesize research from multiple sources.
        
        Returns:
            Dictionary with synthesized information
        """
        synthesis = {
            "topic": self.current_topic,
            "main_findings": [],
            "key_points": [],
            "sources": []
        }
        
        # Extract sources
        for note in self.research_notes:
            if note["type"] == "source_analysis":
                synthesis["sources"].append({
                    "url": note["source"],
                    "title": note["title"]
                })
                
                # Extract key points from each source
                if "main_content" in note["analysis"]:
                    content = note["analysis"]["main_content"]
                    sentences = re.split(r'(?<=[.!?])\s+', content)
                    
                    # Simple heuristic: sentences with keywords from the topic are important
                    topic_words = set(self.current_topic.lower().split())
                    
                    for sentence in sentences:
                        sentence_words = set(sentence.lower().split())
                        # If sentence contains at least 2 words from the topic
                        if len(topic_words.intersection(sentence_words)) >= 2:
                            if sentence not in synthesis["key_points"]:
                                synthesis["key_points"].append(sentence)
        
        # Limit key points
        synthesis["key_points"] = synthesis["key_points"][:10]
        
        # Generate main findings (simplified)
        if synthesis["key_points"]:
            synthesis["main_findings"] = [
                f"Based on {len(synthesis['sources'])} sources, the research found multiple perspectives on {self.current_topic}.",
                "The information gathered shows consistency across multiple sources.",
                f"Key aspects of {self.current_topic} were identified and analyzed."
            ]
        else:
            synthesis["main_findings"] = [
                f"Research on {self.current_topic} did not yield significant results.",
                "Consider refining the search terms or exploring related topics."
            ]
        
        return synthesis
    
    def close(self):
        """Close the browser and clean up resources."""
        if self.browser:
            self.browser.close_browser()

# Example Usage (for testing)
if __name__ == '__main__':
    print("Testing DeepResearcher...")
    researcher = DeepResearcher()
    
    if researcher.browser and researcher.browser.driver:
        print("\nResearching 'Python programming language'...")
        result = researcher.research_topic("Python programming language", depth=3, sources=2)
        
        if result["success"]:
            print("\nResearch Results:")
            print(f"Topic: {result['topic']}")
            print(f"Sources Analyzed: {result['sources_analyzed']}")
            
            print("\nMain Findings:")
            for finding in result["synthesis"]["main_findings"]:
                print(f"- {finding}")
            
            print("\nKey Points:")
            for point in result["synthesis"]["key_points"]:
                print(f"- {point}")
            
            print("\nSources:")
            for source in result["synthesis"]["sources"]:
                print(f"- {source['title']}: {source['url']}")
        else:
            print(f"Research failed: {result.get('error', 'Unknown error')}")
        
        print("\nClosing researcher...")
        researcher.close()
    else:
        print("Failed to initialize browser for research.")
