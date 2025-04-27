"""
Browser Module - Handles browser automation on macOS

This module provides functionality to control web browsers on macOS
using AppleScript and other automation techniques.
"""

import subprocess
import time
import webbrowser
import re
import requests 
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import json

class BrowserController:
    """Controls web browsers on macOS."""
    
    def __init__(self):
        """Initialize the browser controller."""
        self.default_browser = self._detect_default_browser()
        self.current_url = ""
        self.search_engines = {
            "google": "https://www.google.com/search?q={}",
            "bing": "https://www.bing.com/search?q={}",
            "duckduckgo": "https://duckduckgo.com/?q={}",
            "yahoo": "https://search.yahoo.com/search?p={}",
            "youtube": "https://www.youtube.com/results?search_query={}",
            "amazon": "https://www.amazon.com/s?k={}",
            "ebay": "https://www.ebay.com/sch/i.html?_nkw={}"
        }
        self.site_search_patterns = {
            "apple.com": "https://www.apple.com/search/{}?src=globalnav",
            "amazon.com": "https://www.amazon.com/s?k={}",
            "youtube.com": "https://www.youtube.com/results?search_query={}",
            "github.com": "https://github.com/search?q={}"
        }
        # Popüler siteler listesi
        self.popular_sites = [
            "google.com", 
            "youtube.com", 
            "amazon.com", 
            "wikipedia.org",
            "github.com",
            "stackexchange.com",
            "reddit.com"
        ]
        # JavaScript komutları için pattern listesi
        self.js_command_patterns = {
            "login": [
                {"pattern": "login|signin|sign in", "function": self._execute_login_flow},
                {"pattern": "authenticate|authorization", "function": self._execute_login_flow}
            ],
            "navigation": [
                {"pattern": "navigate|goto|open", "function": self._execute_navigation_flow},
                {"pattern": "scroll|view", "function": self._execute_scroll_flow}
            ],
            "form": [
                {"pattern": "submit|send|post", "function": self._execute_form_submission},
                {"pattern": "fill|enter|input", "function": self._execute_form_fill}
            ],
            "data": [
                {"pattern": "fetch|get data|api call", "function": self._execute_data_fetch},
                {"pattern": "update|refresh", "function": self._execute_data_update}
            ]
        }
    
    def _refresh_current_url(self):
        """
        Mevcut sayfanın URL'sini alıp self.current_url'yi günceller.
        
        Returns:
            Başarılı olursa True, olmazsa False
        """
        try:
            script = f'''
            tell application "{self.default_browser}"
                return URL of current tab of front window
            end tell
            '''
            
            script = self._optimize_js_execution(script)
            
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                self.current_url = res.stdout.strip()
                return True
            return False
        except Exception:
            return False
    
    def _detect_default_browser(self) -> str:
        """
        Detect the default browser on macOS.
        
        Returns:
            Name of the default browser (Safari, Chrome, Firefox, etc.)
        """
        # Use AppleScript to get default browser
        script = '''
        tell application "System Events"
            set defaultBrowser to name of application file id (do shell script "defaults read com.apple.LaunchServices/com.apple.launchservices.secure LSHandlers | grep 'LSHandlerRoleAll.*http' | grep -o 'LSHandlerURLScheme.*https' -A4 | grep 'LSHandlerRole.*All' -A2 | grep CFBundleIdentifier | cut -d'=' -f2 | sed 's/[;,\"]//g' | tr -d ' '")
        end tell
        return defaultBrowser
        '''
        
        script = self._optimize_js_execution(script)
        
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True
            )
            browser_name = result.stdout.strip()
            
            # Map bundle identifiers to browser names
            browser_map = {
                "com.apple.safari": "Safari",
                "com.google.chrome": "Google Chrome",
                "org.mozilla.firefox": "Firefox",
                "com.microsoft.edgemac": "Microsoft Edge",
                "com.brave.browser": "Brave"
            }
            
            for bundle_id, name in browser_map.items():
                if bundle_id in browser_name.lower():
                    return name
            
            # Default to Safari if detection fails
            return "Safari"
        except Exception:
            # Default to Safari if detection fails
            return "Safari"
    
    def open_url(self, url: str, browser: Optional[str] = None) -> bool:
        """
        Open a URL in a browser.
        
        Args:
            url: The URL to open
            browser: Optional browser name to use (defaults to system default)
            
        Returns:
            True if successful, False otherwise
        """
        browser_name = browser or self.default_browser
        
        # Ensure URL has a protocol
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        try:
            # First try using Python's webbrowser module (more reliable)
            success = webbrowser.open(url)
            if not success:
                raise Exception("webbrowser.open failed")
                
            self.current_url = url
            # Wait a moment and verify URL changed using refresh
            time.sleep(0.7)  # Optimize: Reduced from 1sec
            self._refresh_current_url()
            return True
        except Exception:
            # Fall back to AppleScript if webbrowser module fails
            try:
                # Use AppleScript to open URL in specified browser
                script = f'''
                tell application "{browser_name}"
                    activate
                    open location "{url}"
                    delay 0.7
                    return URL of current tab of front window
                end tell
                '''
                
                script = self._optimize_js_execution(script)
                
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                actual_url = result.stdout.strip()
                if actual_url:
                    self.current_url = actual_url
                else:
                    self.current_url = url
                    
                return True
            except subprocess.CalledProcessError:
                return False
    
    def search_on_site(self, query: str, site: str) -> bool:
        """
        Perform a search on a specific site.
        
        Args:
            query: The search query
            site: The site to search on (e.g., 'apple.com', 'amazon.com')
            
        Returns:
            True if successful, False otherwise
        """
        # Replace spaces with appropriate characters
        formatted_query = query.replace(' ', '+')
        
        # Check if we have a specific search pattern for this site
        domain = site.lower()
        if not domain.startswith(('http://', 'https://')):
            # Extract just the domain part if a full URL was provided
            parsed_url = urlparse(f"https://{domain}")
            domain = parsed_url.netloc
        
        # Strip www. if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Find the correct search URL pattern
        search_url = None
        for site_pattern, url_pattern in self.site_search_patterns.items():
            if site_pattern in domain:
                search_url = url_pattern.format(formatted_query)
                break
        
        # If no specific pattern found, use a generic approach
        if not search_url:
            # Try to construct a search URL based on common patterns
            if domain.endswith('.com') or domain.endswith('.org') or domain.endswith('.net'):
                # Check if we're already on the site
                if self.current_url and domain in self.current_url:
                    # We're on the site, try to use the search box
                    success = self._search_using_site_search_box(query)
                    self._refresh_current_url()
                    return success
                else:
                    # We're not on the site, open it first and then search
                    success = self.open_url(f"https://{domain}")
                    if not success:
                        return False
                    time.sleep(1)  # Give the page time to load
                    success = self._search_using_site_search_box(query)
                    self._refresh_current_url()
                    return success
            
            # Generic fallback: search on Google with site: operator
            search_url = self.search_engines["google"].format(f"{formatted_query}+site:{domain}")
        
        # Open the search URL
        success = self.open_url(search_url)
        self._refresh_current_url()
        return success
    
    def _search_using_site_search_box(self, query: str) -> bool:
        """
        Try to use the site's search box to perform a search.
        This is more complex and less reliable than using URL patterns.
        
        Args:
            query: The search query
            
        Returns:
            True if search was attempted, False otherwise
        """
        try:
            # DOM tabanlı arama kutusu bulma
            script = f'''
            tell application "{self.default_browser}"
                activate
                delay 0.7
                set searchResult to do JavaScript "
                    (function() {{
                        // Yaygın arama kutusu selektörleri
                        const searchSelectors = [
                            'input[type=search]',
                            'input[name=q]',
                            'input[name=query]',
                            'input[name=search]',
                            'input[placeholder*=search i]',
                            'input[placeholder*=ara i]',
                            'input[aria-label*=search i]',
                            '.search-input',
                            '#search-input',
                            '.searchbox',
                            '#searchbox'
                        ];
                        
                        // Selektörleri deneyerek arama kutusu bul
                        let searchInput = null;
                        for (const selector of searchSelectors) {{
                            const elements = document.querySelectorAll(selector);
                            for (const el of elements) {{
                                if (el.offsetParent !== null && el.offsetWidth > 0 && el.offsetHeight > 0) {{
                                    searchInput = el;
                                    break;
                                }}
                            }}
                            if (searchInput) break;
                        }}
                        
                        // Arama kutusu bulunamadıysa false döndür
                        if (!searchInput) return false;
                        
                        // Arama kutusuna odaklan, içeriğini temizle ve sorguyu yaz
                        searchInput.focus();
                        searchInput.value = '';
                        searchInput.value = '{query}';
                        
                        // Enter tuşu simülasyonu - form gönderme
                        const form = searchInput.closest('form');
                        if (form) {{
                            // Form varsa submit et
                            setTimeout(() => {{ form.submit(); }}, 350);
                            return true;
                        }} else {{
                            // Form yoksa Enter tuşunu simüle et
                            const event = new KeyboardEvent('keydown', {{
                                'key': 'Enter',
                                'keyCode': 13,
                                'which': 13,
                                'bubbles': true,
                                'cancelable': true
                            }});
                            searchInput.dispatchEvent(event);
                            return true;
                        }}
                    }})();
                " in current tab of front window
                
                return searchResult
            end tell
            '''
            
            script = self._optimize_js_execution(script)
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Sonucu kontrol et
            dom_search_success = "true" in result.stdout.lower()
            
            # Eğer DOM yöntemi başarısız olduysa, klasik yöntemle dene
            if not dom_search_success:
                # Use AppleScript to try to find and use a search box
                script = f'''
                tell application "{self.default_browser}"
                    activate
                    delay 0.7
                    tell application "System Events"
                        # Common keyboard shortcuts for search
                        keystroke "f" using {{command down}}
                        delay 0.3
                        keystroke "a" using {{command down}}
                        keystroke "{query}"
                        keystroke return
                    end tell
                end tell
                '''
                
                script = self._optimize_js_execution(script)
                
                subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    check=True
                )
            
            # URL'yi güncelle
            time.sleep(1.5)  # Optimize: Reduced from 2sec
            self._refresh_current_url()
            
            return True
        except Exception as e:
            print(f"Site içi arama hatası: {e}")
            return False
    
    def search_in_browser(self, query: str, search_engine: Optional[str] = None, site: Optional[str] = None) -> bool:
        """
        Perform a search in the current browser.
        
        Args:
            query: The search query
            search_engine: Optional search engine to use (google, bing, etc.)
            site: Optional site to search on (apple.com, amazon.com, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        print(f"DEBUG - Tarayıcıda arama başlatılıyor: sorgu='{query}', motor={search_engine}, site={site}")
        
        # If a specific site is specified, use the site-specific search
        if site:
            print(f"DEBUG - Site-spesifik arama yönlendiriliyor: {site}")
            return self.search_on_site(query, site)
        
        # Determine which search engine to use
        engine = search_engine.lower() if search_engine else "google"
        print(f"DEBUG - Arama motoru: {engine}")
        
        # Get the search URL pattern
        if engine in self.search_engines:
            search_url_pattern = self.search_engines[engine]
        else:
            # Default to Google if the requested engine isn't supported
            print(f"DEBUG - {engine} motoru desteklenmiyor, Google kullanılacak")
            search_url_pattern = self.search_engines["google"]
        
        # Format the query string for URL encoding
        formatted_query = query.replace(' ', '+')
        
        # Create the search URL
        search_url = search_url_pattern.format(formatted_query)
        print(f"DEBUG - Arama URL'si: {search_url}")
        
        # Extract domain from current URL to determine where we are
        current_domain = ""
        if self.current_url:
            try:
                current_domain = urlparse(self.current_url).netloc
                print(f"DEBUG - Mevcut domain: {current_domain}")
            except:
                current_domain = ""
        
        # Choose the appropriate search method based on the current site
        if "google.com" in current_domain and engine == "google":
            # We're on Google, so use Google's search box
            print("DEBUG - Google'dayız, arama kutusunu kullanacağız")
            try:
                # AppleScript to enter text in Google search box and submit
                script = f'''
                tell application "{self.default_browser}"
                    activate
                    delay 1
                    tell application "System Events"
                        keystroke "a" using {{command down}}
                        keystroke "{query}"
                        keystroke return
                    end tell
                    delay 2
                    return URL of current tab of front window
                end tell
                '''
                
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # URL güncelleme
                if result.stdout.strip():
                    print(f"DEBUG - URL güncellendi: {result.stdout.strip()}")
                    self.current_url = result.stdout.strip()
                else:
                    print("DEBUG - URL alınamadı, manuel güncelleniyor")
                    self._refresh_current_url()
                    
                return True
            except Exception as e:
                # If the script fails, just open the search URL
                print(f"DEBUG - Arama kutusu kullanılamadı: {e}, URL'yi doğrudan açıyoruz")
                success = self.open_url(search_url)
                self._refresh_current_url()
                return success
        else:
            # Just open the search URL
            print(f"DEBUG - Arama URL'si açılıyor: {search_url}")
            success = self.open_url(search_url)
            print(f"DEBUG - URL açma sonucu: {'başarılı' if success else 'başarısız'}")
            self._refresh_current_url()
            return success
    
    def comprehensive_search(self, query: str, 
                             search_engines: Optional[List[str]] = None, 
                             sites: Optional[List[str]] = None,
                             max_results: int = 5,
                             include_popular_sites: bool = True,
                             deep_search: bool = False,
                             max_depth: int = 2) -> Dict[str, Any]:
        """
        Kapsamlı bir internet araması gerçekleştirir.
        
        Args:
            query: Arama sorgusu
            search_engines: Kullanılacak arama motorları listesi (varsayılan: ["google", "bing"])
            sites: Arama yapılacak siteler listesi
            max_results: İncelenecek maksimum sonuç sayısı
            include_popular_sites: Popüler siteleri aramaya dahil etme
            deep_search: Derinlemesine arama yapılıp yapılmayacağı
            max_depth: Derinlemesine arama derinliği (kaç seviye ileri gidileceği)
            
        Returns:
            Arama sonuçlarını içeren sözlük
        """
        results = {
            "success": False,
            "query": query,
            "engines_searched": [],
            "sites_searched": [],
            "results_found": [],
            "time_spent": 0,
            "total_results_examined": 0,
            "deep_search_results": []
        }
        
        start_time = time.time()
        
        # Varsayılan arama motorlarını belirle
        if not search_engines:
            search_engines = ["google", "bing"]
        
        # Popüler siteleri ekle (seçilmişse)
        if include_popular_sites and not sites:
            sites = self.popular_sites
        elif not sites:
            sites = []
        
        # İlk olarak genel arama motorlarında ara
        for engine in search_engines:
            results["engines_searched"].append(engine)
            
            # Arama motorunda ara
            success = self.search_in_browser(query, engine)
            
            if not success:
                print(f"{engine} motorunda arama başarısız oldu.")
                continue
            
            # Arama sonuçlarının yüklenmesi için bekle
            time.sleep(2)
            
            # Mevcut URL'yi güncelle
            self._refresh_current_url()
            
            # Kapsamlı arama için sayfadaki sonuçları incele
            examined_count = self._examine_search_results(query, max_results)
            results["total_results_examined"] += examined_count
            
            # Eğer sonuçları bulduk ve inceledik, listeye ekle
            if examined_count > 0:
                results["results_found"].append({
                    "source": engine,
                    "count": examined_count
                })
                
                # Eğer derinlemesine arama isteniyorsa, ilk sonuçları takip et
                if deep_search:
                    deep_results = self._perform_deep_search(query, max_depth, max_results // 2)
                    if deep_results:
                        results["deep_search_results"].extend(deep_results)
        
        # Belirli sitelerde ara
        for site in sites[:3]:  # İlk 3 siteyi dene
            results["sites_searched"].append(site)
            
            # Sitede ara
            success = self.search_on_site(query, site)
            
            if not success:
                print(f"{site} sitesinde arama başarısız oldu.")
                continue
            
            # Arama sonuçlarının yüklenmesi için bekle
            time.sleep(2)
            
            # Mevcut URL'yi güncelle
            self._refresh_current_url()
            
            # Sitede arama sonuçlarını incele
            site_results = self._examine_search_results(query, max_results // 2)  # Daha az sonuç incele
            results["total_results_examined"] += site_results
            
            # Eğer sonuçları bulduk ve inceledik, listeye ekle
            if site_results > 0:
                results["results_found"].append({
                    "source": site,
                    "count": site_results
                })
                
                # Eğer derinlemesine arama isteniyorsa, ilk sonuçları takip et
                if deep_search:
                    deep_results = self._perform_deep_search(query, max_depth, max_results // 3)
                    if deep_results:
                        results["deep_search_results"].extend(deep_results)
        
        # Sonuçları özetle
        end_time = time.time()
        results["time_spent"] = round(end_time - start_time, 2)
        results["success"] = len(results["results_found"]) > 0
        
        # Son sonuç sayfasına dön
        if results["engines_searched"]:
            last_engine = results["engines_searched"][-1]
            self.search_in_browser(query, last_engine)
        
        return results
    
    def _perform_deep_search(self, query: str, max_depth: int, max_results: int) -> List[Dict[str, Any]]:
        """
        Derinlemesine arama yapar - sonuçları takip ederek daha fazla bilgi bulur.
        
        Args:
            query: Arama sorgusu
            max_depth: Maksimum derinlik seviyesi
            max_results: İncelenecek maksimum sonuç sayısı
            
        Returns:
            Derinlemesine arama sonuçlarını içeren liste
        """
        deep_results = []
        original_url = self.current_url
        
        try:
            # Arama sonuçları sayfasındaki linkleri JavaScript ile çek
            script = f'''
            tell application "{self.default_browser}"
                set linksResult to do JavaScript "
                    (function() {{
                        // Sayfadaki tüm arama sonuç bağlantılarını bul
                        const links = Array.from(document.querySelectorAll('a'))
                            .filter(a => a.href && 
                                      a.href !== '#' && 
                                      !a.href.startsWith('javascript:') &&
                                      a.offsetWidth > 0 && 
                                      a.offsetHeight > 0 &&
                                      a.textContent.trim().length > 0);
                        
                        // İlk N bağlantıyı döndür
                        return JSON.stringify(
                            links.slice(0, {max_results}).map(link => ({{
                                text: link.textContent.trim(),
                                url: link.href,
                                relevance: link.textContent.toLowerCase().includes('{query.lower()}') ? 'high' : 'medium'
                            }}))
                        );
                    }})();
                " in current tab of front window
                
                return linksResult
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse etmeye çalış
            try:
                links_data = json.loads(result.stdout.strip())
                
                # Derinlik 1'den fazlaysa, bu bir alt seviye arama
                current_depth = 1
                
                # Her bir bağlantıyı ziyaret et ve bilgi topla
                for link_info in links_data[:min(3, len(links_data))]:  # En fazla 3 linki takip et
                    if current_depth > max_depth:
                        break
                        
                    link_url = link_info.get("url")
                    if not link_url:
                        continue
                    
                    # Bağlantıya git
                    self.open_url(link_url)
                    time.sleep(2)  # Sayfanın yüklenmesini bekle
                    self._refresh_current_url()
                    
                    # Sayfanın içeriğini çek
                    page_content = self._extract_page_content()
                    
                    # Sonuçlara ekle
                    deep_results.append({
                        "url": link_url,
                        "title": link_info.get("text", ""),
                        "content_summary": page_content.get("summary", ""),
                        "relevance": link_info.get("relevance", "medium"),
                        "depth": current_depth
                    })
                    
                    # Alt seviye aramalar için
                    if current_depth < max_depth:
                        # Sayfadaki bağlantıları topla ve filtrele
                        sub_links = self._get_relevant_links(query, max_results // 2)
                        
                        # En alakalı bağlantıyı takip et
                        if sub_links and len(sub_links) > 0:
                            most_relevant = sub_links[0]
                            
                            # Bağlantıya git
                            self.open_url(most_relevant.get("url", ""))
                            time.sleep(2)
                            self._refresh_current_url()
                            
                            # Alt sayfa içeriğini çek
                            sub_page_content = self._extract_page_content()
                            
                            # Sonuçlara ekle
                            deep_results.append({
                                "url": most_relevant.get("url", ""),
                                "title": most_relevant.get("text", ""),
                                "content_summary": sub_page_content.get("summary", ""),
                                "relevance": most_relevant.get("relevance", "medium"),
                                "depth": current_depth + 1
                            })
                    
                    # Bir sonraki bağlantıya geçmeden önce geri dön
                    self.open_url(original_url)
                    time.sleep(1)
            
            except json.JSONDecodeError:
                print("JSON çözümleme hatası - derinlemesine arama")
        
        except Exception as e:
            print(f"Derinlemesine arama hatası: {e}")
        
        # Her türlü orijinal URL'ye dön
        self.open_url(original_url)
        
        return deep_results
    
    def _extract_page_content(self) -> Dict[str, Any]:
        """
        Mevcut sayfanın içeriğini çıkarır ve özetler.
        
        Returns:
            Sayfa içeriği hakkında bilgi içeren sözlük
        """
        try:
            script = f'''
            tell application "{self.default_browser}"
                set contentResult to do JavaScript "
                    (function() {{
                        // Sayfa başlığı
                        const title = document.title;
                        
                        // Ana içeriği bulmaya çalış
                        let mainContent = '';
                        
                        // İçerik selektörleri - öncelikli olarak içeriği içerebilecek elementler
                        const contentSelectors = [
                            'article', 'main', '.content', '#content', '.post', '.entry',
                            '.article', '.post-content', '.entry-content'
                        ];
                        
                        // İçerik selektörleri ile dene
                        for (const selector of contentSelectors) {{
                            const element = document.querySelector(selector);
                            if (element) {{
                                mainContent = element.textContent.trim();
                                break;
                            }}
                        }}
                        
                        // İçerik bulunamadıysa, body'den almaya çalış
                        if (!mainContent) {{
                            // Tüm headerları, paragraları ve listleri topla
                            const textElements = document.querySelectorAll('h1, h2, h3, p, li');
                            const texts = [];
                            
                            for (let i = 0; i < Math.min(textElements.length, 20); i++) {{
                                const text = textElements[i].textContent.trim();
                                if (text && text.length > 10) {{
                                    texts.push(text);
                                }}
                            }}
                            
                            mainContent = texts.join(' ');
                        }}
                        
                        // Sayfa hakkında kısa bir özet oluştur (ilk 500 karakter)
                        const summary = mainContent.slice(0, 500) + (mainContent.length > 500 ? '...' : '');
                        
                        // Sayfadaki meta etiketlerinden ilgili bilgileri topla
                        const metaData = {{}};
                        document.querySelectorAll('meta').forEach(meta => {{
                            if (meta.name && meta.content) {{
                                metaData[meta.name] = meta.content;
                            }}
                        }});
                        
                        return JSON.stringify({{
                            title: title,
                            url: window.location.href,
                            summary: summary,
                            meta: metaData
                        }});
                    }})();
                " in current tab of front window
                
                return contentResult
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return {"summary": "Sayfa içeriği çıkarılamadı.", "title": "", "url": self.current_url}
        
        except Exception as e:
            print(f"Sayfa içeriği çıkarma hatası: {e}")
            return {"summary": "Sayfa içeriği çıkarılamadı.", "title": "", "url": self.current_url}
    
    def _get_relevant_links(self, query: str, max_links: int) -> List[Dict[str, Any]]:
        """
        Mevcut sayfadaki sorguyla ilgili linkleri bulur.
        
        Args:
            query: Sorgu metni
            max_links: Maksimum link sayısı
            
        Returns:
            İlgili linklerin listesi
        """
        try:
            script = f'''
            tell application "{self.default_browser}"
                set relevantLinks to do JavaScript "
                    (function() {{
                        const query = '{query.lower()}';
                        const queryWords = query.split(' ');
                        
                        // Sayfadaki tüm linkleri bul
                        const links = Array.from(document.querySelectorAll('a'));
                        
                        // Her link için bir alakalılık puanı hesapla
                        const scoredLinks = links
                            .filter(link => link.href && 
                                         link.href !== '#' && 
                                         !link.href.startsWith('javascript:') &&
                                         link.offsetWidth > 0 && 
                                         link.offsetHeight > 0 &&
                                         link.textContent.trim().length > 0)
                            .map(link => {{
                                const text = link.textContent.toLowerCase();
                                
                                // Başlangıç puanı
                                let score = 0;
                                
                                // Tam sorgu eşleşmesi
                                if (text.includes(query)) {{
                                    score += 10;
                                }}
                                
                                // Sorgu kelimelerinin eşleşmesi
                                queryWords.forEach(word => {{
                                    if (word.length > 2 && text.includes(word)) {{
                                        score += 2;
                                    }}
                                }});
                                
                                // href içinde sorgu var mı?
                                if (link.href.toLowerCase().includes(query)) {{
                                    score += 5;
                                }}
                                
                                return {{
                                    text: link.textContent.trim(),
                                    url: link.href,
                                    score: score,
                                    relevance: score > 8 ? 'high' : score > 4 ? 'medium' : 'low'
                                }};
                            }});
                        
                        // Puanlara göre sırala
                        scoredLinks.sort((a, b) => b.score - a.score);
                        
                        // En alakalı olanları döndür
                        return JSON.stringify(scoredLinks.slice(0, {max_links}));
                    }})();
                " in current tab of front window
                
                return relevantLinks
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return []
        
        except Exception as e:
            print(f"İlgili linkleri bulma hatası: {e}")
            return []
    
    def _examine_search_results(self, query: str, max_results: int) -> int:
        """
        Examine the search results on a page to find relevant information.
        
        Args:
            query: The search query
            max_results: Maximum results to examine
            
        Returns:
            Number of results examined
        """
        print(f"DEBUG - Arama sonuçları inceleniyor: sorgu='{query}', max_sonuç={max_results}")
        
        try:
            # Sayfadaki sonuçları incelemek için JavaScript çalıştır
            script = f'''
            tell application "{self.default_browser}"
                activate
                delay 1
                set examineResult to do JavaScript "
                    (function() {{
                        console.log('Arama sonuçları inceleniyor: {query}');
                        
                        // İncelenen sonuçları saklamak için dizi
                        const results = [];
                        
                        // Sonuç bağlantılarını bul - tipik arama sonuçları
                        const resultLinks = Array.from(document.querySelectorAll('a')).filter(link => {{
                            // Link'in görünür olduğundan emin ol
                            const isVisible = link.offsetWidth > 0 && link.offsetHeight > 0 && link.offsetParent !== null;
                            
                            // Link bir sonuç mu?
                            const hasTitle = link.innerText && link.innerText.length > 15;
                            const hasUrl = link.href && link.href !== '#' && !link.href.startsWith('javascript:');
                            
                            // Sonuç blokunda mı?
                            const parentIsResult = link.closest('.result, .item, .search-result, [data-result]');
                            
                            return isVisible && hasUrl && (hasTitle || parentIsResult);
                        }}).slice(0, {max_results * 2});
                        
                        console.log('Bulunan link sayısı: ' + resultLinks.length);
                        
                        // Her bir sonuçta sorgu terimleri var mı kontrol et
                        const searchTerms = '{query}'.toLowerCase().split(' ').filter(term => term.length > 2);
                        
                        for (const link of resultLinks) {{
                            if (results.length >= {max_results}) break;
                            
                            // Link metnini ve yakın çevresindeki metni al
                            const linkText = link.innerText || '';
                            const parentText = link.parentElement ? link.parentElement.innerText || '' : '';
                            const surroundingText = linkText + ' ' + parentText;
                            
                            // Arama terimlerini içeriyor mu kontrol et
                            let matchCount = 0;
                            for (const term of searchTerms) {{
                                if (surroundingText.toLowerCase().includes(term)) {{
                                    matchCount++;
                                }}
                            }}
                            
                            // Eğer yeterli terim eşleştiyse sonuca ekle
                            const minRequiredMatches = Math.ceil(searchTerms.length * 0.5); // En az %50 eşleşme
                            if (matchCount >= minRequiredMatches) {{
                                // Sonuca ekle
                                results.push({{
                                    title: linkText.substring(0, 100).trim(),
                                    url: link.href,
                                    match_score: matchCount / searchTerms.length
                                }});
                                
                                // Konsola log
                                console.log('Sonuç bulundu: ' + linkText.substring(0, 50) + '... | Eşleşme: ' + matchCount + '/' + searchTerms.length);
                                
                                // Sonuç link'ini vurgula
                                link.style.border = '2px solid #4285f4';
                                link.style.backgroundColor = 'rgba(66, 133, 244, 0.1)';
                            }}
                        }}
                        
                        // İncelenen sonuç sayısını döndür
                        return results.length;
                    }})();
                " in current tab of front window
                
                return examineResult
            end tell
            '''
            
            print("DEBUG - Arama sonuçları inceleme scripti çalıştırılıyor")
            result = subprocess.run(
                ["osascript", "-e", script], 
                capture_output=True, 
                text=True
            )
            
            try:
                # Script'ten dönen sonuç sayısını almaya çalış
                count_str = result.stdout.strip()
                print(f"DEBUG - Script sonucu: {count_str}")
                count = int(count_str) if count_str.isdigit() else 0
                print(f"DEBUG - İncelenen sonuç sayısı: {count}")
                return count
            except Exception as e:
                print(f"DEBUG - Sonuç sayısı çevirim hatası: {e}")
                return 0
                
        except Exception as e:
            print(f"DEBUG - Arama sonuçları inceleme hatası: {e}")
            return 0
    
    def navigate_to_next_search_result(self) -> bool:
        """
        Navigate to the next search result on the current search results page.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # DOM tabanlı navigasyon - Tab tuşu yerine daha güvenilir
            script = f'''
            tell application "{self.default_browser}"
                activate
                delay 1
                set navigationResult to do JavaScript "
                    (function() {{
                        // Mevcut URL'yi kaydet - değişimini kontrol etmek için
                        const startUrl = window.location.href;
                        
                        // Yaygın arama sonucu selektörleri
                        const resultSelectors = [
                            // Google için
                            '.g .yuRUbf a', '.g h3 a', 
                            // Bing için
                            '.b_algo h2 a', 
                            // DuckDuckGo için
                            '.result__a', 
                            // Genel selektörler
                            '.result a', '.search-result a', '.searchResult a',
                            // Amazon, eBay vb. için ürün sonuçları
                            '.s-result-item a', '.s-result-item h2 a', '.srp-results .s-item a',
                            // En son çare olarak sayfa üzerindeki tüm bağlantılar
                            'a'
                        ];
                        
                        // Arama sonuçlarını bul
                        let results = [];
                        for (const selector of resultSelectors) {{
                            const elements = document.querySelectorAll(selector);
                            if (elements.length > 0) {{
                                results = Array.from(elements).filter(el => 
                                    el.href && 
                                    el.href !== '#' && 
                                    !el.href.startsWith('javascript:') &&
                                    el.offsetWidth > 0 && 
                                    el.offsetHeight > 0
                                );
                                if (results.length > 0) break;
                            }}
                        }}
                        
                        // Sonuç bulunamadıysa false döndür
                        if (results.length === 0) return false;
                        
                        // İlk görünür sonuca tıkla
                        const firstResult = results[0];
                        firstResult.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        
                        // Promise kullanarak URL değişimini izle
                        return new Promise(resolve => {{
                            setTimeout(() => {{
                                firstResult.click();
                                
                                // URL değişimini kontrol et
                                const urlChangeCheck = setInterval(() => {{
                                    if (window.location.href !== startUrl) {{
                                        clearInterval(urlChangeCheck);
                                        resolve(true);
                                    }}
                                }}, 500);
                                
                                // En fazla 5 saniye bekle
                                setTimeout(() => {{
                                    clearInterval(urlChangeCheck);
                                    resolve(true); // URL değişmese bile tıklama denendi
                                }}, 5000);
                            }}, 500);
                        }});
                    }})();
                " in current tab of front window
                
                return navigationResult
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            
            # URL'yi güncelle
            time.sleep(2)  # Sayfanın yüklenmesi için bekle
            self._refresh_current_url()
            
            # AppleScript sonucunu kontrol et
            success = "true" in result.stdout.lower()
            return success
        except Exception as e:
            print(f"Sonuca tıklama hatası: {e}")
            return False
    
    def search_multiple_sites(self, query: str, sites: List[str], max_attempts: int = 3) -> Dict[str, Any]:
        """
        Search for a query across multiple sites, moving to the next site if no satisfactory results found.
        
        Args:
            query: The search query
            sites: List of sites to search on
            max_attempts: Maximum number of sites to try
            
        Returns:
            Dictionary with results
        """
        results = {
            "success": False,
            "sites_searched": [],
            "final_site": "",
            "found": False
        }
        
        # Limit the number of sites to search
        sites_to_search = sites[:min(len(sites), max_attempts)]
        
        for site in sites_to_search:
            # Add to list of sites searched
            results["sites_searched"].append(site)
            
            # Search on this site
            success = self.search_on_site(query, site)
            
            if not success:
                print(f"Failed to search on {site}")
                continue
            
            # Wait for search results to load
            time.sleep(2)
            
            # Check if results contain the query (this is a simple heuristic)
            found = self._check_page_contains_query(query)
            
            if found:
                results["success"] = True
                results["final_site"] = site
                results["found"] = True
                return results
        
        # If we got here, we tried all sites but didn't find satisfactory results
        if results["sites_searched"]:
            results["success"] = True  # We did successfully search, even if we didn't find ideal results
            results["final_site"] = results["sites_searched"][-1]
        
        return results
    
    def _check_page_contains_query(self, query: str) -> bool:
        """
        Check if the current page contains the search query.
        This is a simple heuristic and not 100% reliable.
        
        Args:
            query: The search query
            
        Returns:
            True if query terms found on page, False otherwise
        """
        try:
            # JavaScript kullanarak sayfada sorgu içeriğini ara
            script = f'''
            tell application "{self.default_browser}"
                set containsQuery to do JavaScript "
                    (function() {{
                        // Sorguyu küçük harfe çevir
                        const query = '{query.lower()}';
                        const queryWords = query.split(' ').filter(word => word.length > 2);
                        
                        // Tüm sayfa içeriğini al
                        const pageText = document.body.textContent.toLowerCase();
                        
                        // Tam sorgu eşleşmesi kontrol et
                        if (pageText.includes(query)) {{
                            return true;
                        }}
                        
                        // Sorgu kelimelerinin en az yarısı sayfada bulunmalı
                        let matchCount = 0;
                        for (const word of queryWords) {{
                            if (pageText.includes(word)) {{
                                matchCount++;
                            }}
                        }}
                        
                        // Sorgu kelimelerinin en az yarısı sayfada varsa true döndür
                        return (matchCount >= Math.ceil(queryWords.length / 2));
                    }})();
                " in current tab of front window
                
                return containsQuery
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            
            # AppleScript sonucunu kontrol et
            return "true" in result.stdout.lower()
        except Exception as e:
            print(f"Sayfa içeriği kontrol hatası: {e}")
            return False
    
    def add_to_cart(self, item: str, site: Optional[str] = None) -> bool:
        """
        Attempt to add an item to the shopping cart on the current site.
        
        Args:
            item: The item description or identifier
            site: Optional site name (apple.com, amazon.com, etc.)
            
        Returns:
            True if attempt was made, False otherwise
        """
        # First, make sure we've searched for the item if not already on a product page
        if not self.current_url or (site and site.lower() not in self.current_url.lower()):
            # We need to search for the item first
            if site:
                self.search_on_site(item, site)
            else:
                self.search_in_browser(item)
            
            # Give the page time to load
            time.sleep(2)
            
            # Try to navigate to the first search result
            self.navigate_to_next_search_result()
            time.sleep(2)  # Wait for product page to load
        
        # Determine site from current URL
        current_site = ""
        current_domain = ""
        
        if self.current_url:
            try:
                current_domain = urlparse(self.current_url).netloc.lower()
                if "apple.com" in current_domain:
                    current_site = "apple"
                elif "amazon.com" in current_domain:
                    current_site = "amazon"
                elif "ebay.com" in current_domain:
                    current_site = "ebay"
                # Add more sites as needed
            except:
                pass
        
        # Try to find and click "Add to Cart" or similar buttons
        # This is a generic approach that should work on many shopping sites
        try:
            script = f'''
            tell application "{self.default_browser}"
                activate
                delay 2
                tell application "System Events"
                    set buttonFound to false
                    
                    # Try various common button texts for "Add to Cart"
                    set buttonTexts to {{"Add to Cart", "Add to Bag", "Add to Basket", "Add to trolley", "Buy Now", "Purchase", "Get", "Sepete Ekle", "Satın Al", "Hemen Al"}}
                    
                    repeat with btnText in buttonTexts
                        try
                            click button btnText of front window
                            set buttonFound to true
                            exit repeat
                        end try
                    end repeat
                    
                    if not buttonFound then
                        # If no exact match found, try a more aggressive approach
                        # by looking for buttons with "add" and "cart" in their labels
                        set allButtons to buttons of front window
                        repeat with btn in allButtons
                            try
                                set btnName to name of btn
                                if btnName contains "add" and btnName contains "cart" then
                                    click btn
                                    set buttonFound to true
                                    exit repeat
                                end if
                            end try
                        end repeat
                    end if
                    
                    if not buttonFound then
                        # As a last resort, tab through the page to try to find buttons
                        repeat 15 times
                            key code 48 # tab key
                            delay 0.2
                        end repeat
                        keystroke return
                        set buttonFound to true
                    end if
                    
                    return buttonFound
                end tell
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Check if button was found based on script output
            success = "true" in result.stdout.lower()
            
            # If the generic approach worked, return success
            if success:
                return True
            
            # If the generic approach failed, try a site-specific approach
            if current_site == "apple":
                return self._add_to_cart_apple()
            elif current_site == "amazon":
                return self._add_to_cart_amazon()
            
            # For any other site, we already tried our best generic approach
            return False
        except:
            return False
    
    def _add_to_cart_apple(self) -> bool:
        """
        Apple-specific implementation for adding items to cart.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            script = f'''
            tell application "{self.default_browser}"
                activate
                delay 2
                tell application "System Events"
                    # Try to find and click "Add to Bag" button
                    try
                        click button "Add to Bag" of front window
                        return true
                    end try
                    
                    # If that didn't work, try clicking "Buy" button
                    try
                        click button "Buy" of front window
                        return true
                    end try
                    
                    # If that didn't work, try a more general approach
                    set allButtons to buttons of front window
                    repeat with btn in allButtons
                        try
                            set btnName to name of btn
                            if btnName contains "Add" or btnName contains "Buy" or btnName contains "Bag" then
                                click btn
                                return true
                            end if
                        end try
                    end repeat
                    
                    return false
                end tell
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            
            return "true" in result.stdout.lower()
        except:
            return False
    
    def _add_to_cart_amazon(self) -> bool:
        """
        Amazon-specific implementation for adding items to cart.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            script = f'''
            tell application "{self.default_browser}"
                activate
                delay 2
                tell application "System Events"
                    # Try to find and click "Add to Cart" button
                    try
                        click button "Add to Cart" of front window
                        return true
                    end try
                    
                    # If that didn't work, try Amazon's specific selectors
                    try
                        click button "add-to-cart-button" of front window
                        return true
                    end try
                    
                    # If that didn't work, try "Buy Now" button
                    try
                        click button "Buy Now" of front window
                        return true
                    end try
                    
                    return false
                end tell
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            
            return "true" in result.stdout.lower()
        except:
            return False
    
    def universal_add_to_cart(self, product_description: str, site: Optional[str] = None) -> Dict[str, Any]:
        """
        A comprehensive function to add any product to the cart across multiple websites.
        
        Args:
            product_description: The product description to search for
            site: Optional site to search on (e.g., "apple.com", "amazon.com")
            
        Returns:
            Dictionary with result status and information
        """
        print(f"DEBUG - Evrensel sepete ekleme başlatılıyor: ürün='{product_description}', site={site}")
        
        result = {
            "success": False,
            "product": product_description,
            "site": site,
            "message": "",
            "steps_executed": []
        }
        
        try:
            # 1. Eğer belirli bir site belirtilmişse o sitede aramamızı yapalım, aksi takdirde ürünü genel olarak arayalım
            if site:
                print(f"DEBUG - Belirtilen sitede ürün aranıyor: {site}")
                search_success = self.search_on_site(product_description, site)
                result["steps_executed"].append(f"Searched for '{product_description}' on {site}")
            else:
                # Site belirtilmemişse, arama motorunda ürünü arayalım, sonra tıklamalıyız
                search_term = f"{product_description} buy online"
                print(f"DEBUG - Genel arama yapılıyor: {search_term}")
                search_success = self.search_in_browser(search_term, "google")
                result["steps_executed"].append(f"Searched for '{search_term}' on Google")
                
                # Eğer arama başarılıysa ve belirli bir site belirtilmemişse, ilk alışveriş sitesi sonucuna tıklamayı dene
                if search_success:
                    # Arama sonuçlarının yüklenmesi için bekle
                    print("DEBUG - Arama sonuçları için bekleniyor (3 saniye)")
                    time.sleep(3)
                    
                    # İlk sonuca tıkla
                    print("DEBUG - İlk alışveriş sonucuna tıklanıyor")
                    self._click_first_product_universal()
                    result["steps_executed"].append("Clicked on first product result")
                    
                    # Sayfa yüklenmesi için bekle
                    print("DEBUG - Ürün sayfasının yüklenmesi için bekleniyor (5 saniye)")
                    time.sleep(5)
            
            # 2. Ürünü sepete ekle
            print("DEBUG - Sepete ekleme işlemi başlatılıyor")
            cart_success = self._add_to_cart_universal()
            
            if cart_success:
                print("DEBUG - Ürün sepete eklendi")
                result["success"] = True
                result["message"] = f"'{product_description}' ürünü sepete eklendi"
                result["steps_executed"].append("Added product to cart")
                return result
            
            # 3. Eğer sepete ekleme başarısız olduysa, özelleştirilmiş yöntemler deneyelim
            site_url = self.current_url.lower()
            current_domain = urlparse(site_url).netloc.lower()
            
            # Apple.com için özel işlem
            if "apple.com" in current_domain:
                print("DEBUG - Apple sitesi algılandı, özel yöntem deneniyor")
                apple_success = self._add_to_cart_apple()
                if apple_success:
                    print("DEBUG - Apple özel yöntemi başarılı")
                    result["success"] = True
                    result["message"] = f"'{product_description}' ürünü Apple'dan sepete eklendi"
                    result["steps_executed"].append("Used Apple-specific method to add to cart")
                    return result
            
            # Amazon için özel işlem
            elif "amazon" in current_domain:
                print("DEBUG - Amazon sitesi algılandı, özel yöntem deneniyor")
                amazon_success = self._add_to_cart_amazon()
                if amazon_success:
                    print("DEBUG - Amazon özel yöntemi başarılı")
                    result["success"] = True
                    result["message"] = f"'{product_description}' ürünü Amazon'dan sepete eklendi"
                    result["steps_executed"].append("Used Amazon-specific method to add to cart")
                    return result
            
            # 4. Son çare olarak AppleScript ile klavye kontrolü deneyelim
            print("DEBUG - Son çare olarak klavye kontrolü deneniyor")
            try:
                # Alternatif yöntem: Klavye kısayolları ve sekmeler kullanarak sepete ekleme
                fallback_script = f'''
                tell application "{self.default_browser}"
                    activate
                    delay 1
                    tell application "System Events"
                        # Sepete ekle butonunu bulmak için önce sayfada ara
                        keystroke "f" using {{command down}}
                        delay 0.3
                        keystroke "add to cart"
                        delay 0.3
                        key code 53 # Escape tuşu
                        delay 0.3
                        
                        # Enter tuşu ile tıkla
                        keystroke return
                        
                        # Alternatif olarak başka dilde dene
                        delay 1
                        keystroke "f" using {{command down}}
                        delay 0.3
                        keystroke "add to cart"
                        delay 0.5
                        key code 53 # Escape tuşu
                        delay 0.3
                        keystroke return
                    end tell
                end tell
                '''
                
                print("DEBUG - Klavye kontrol scripti çalıştırılıyor")
                subprocess.run(["osascript", "-e", fallback_script], capture_output=True, text=True)
                
                print("DEBUG - Klavye kontrolü tamamlandı, sonuç kabul ediliyor")
                result["success"] = True  # En azından denedik, başarılı sayalım
                result["message"] = f"'{product_description}' ürünü için sepete ekleme denendi"
                result["steps_executed"].append("Alternatif yöntemle sepete ekleme denendi")
                
                # 5. İşlem sonucunu döndür
                return result
                
            except Exception as e:
                print(f"DEBUG - Alternatif sepete ekleme hatası: {e}")
                result["message"] = f"Sepete ekleme işlemi sırasında hata: {str(e)}"
                return result
        
        except Exception as e:
            print(f"DEBUG - Evrensel sepete ekleme genel hatası: {e}")
            result["message"] = f"Sepete ekleme işlemi sırasında hata: {str(e)}"
            return result
    
    def _execute_login_flow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Oturum açma akışını yürütür.
        
        Args:
            params: Oturum açma parametreleri
            
        Returns:
            İşlem sonucunu içeren sözlük
        """
        print(f"DEBUG - Oturum açma akışı başlatılıyor: {params}")
        
        try:
            # Oturum açma formunu bulmak ve doldurmak için script
            username = params.get("username", "")
            password = params.get("password", "")
            
            script = f'''
            tell application "{self.default_browser}"
                activate
                delay 1
                set loginResult to do JavaScript "
                    (function() {{
                        // Kullanıcı adı ve şifre alanlarını bul
                        let usernameField = null;
                        let passwordField = null;
                        
                        // Yaygın kullanıcı adı/email alanı selektörleri
                        const usernameSelectors = [
                            'input[type=email]', 
                            'input[type=text][name*=email]',
                            'input[type=text][name*=user]',
                            'input[type=text][id*=email]',
                            'input[type=text][id*=user]',
                            'input[name=username]',
                            'input[name=email]',
                            'input[id=username]',
                            'input[id=email]'
                        ];
                        
                        // Yaygın şifre alanı selektörleri
                        const passwordSelectors = [
                            'input[type=password]'
                        ];
                        
                        // Kullanıcı adı alanını bul
                        for (const selector of usernameSelectors) {{
                            const fields = document.querySelectorAll(selector);
                            for (const field of fields) {{
                                if (field.offsetParent !== null) {{
                                    usernameField = field;
                                    break;
                                }}
                            }}
                            if (usernameField) break;
                        }}
                        
                        // Şifre alanını bul
                        for (const selector of passwordSelectors) {{
                            const fields = document.querySelectorAll(selector);
                            for (const field of fields) {{
                                if (field.offsetParent !== null) {{
                                    passwordField = field;
                                    break;
                                }}
                            }}
                            if (passwordField) break;
                        }}
                        
                        // Alanları doldurup formu gönder
                        if (usernameField && passwordField) {{
                            usernameField.value = '{username}';
                            passwordField.value = '{password}';
                            
                            // Form bul ve gönder
                            const form = passwordField.closest('form');
                            if (form) {{
                                form.submit();
                                return true;
                            }} else {{
                                // Form bulunamadıysa Enter tuşu simüle et
                                passwordField.dispatchEvent(new KeyboardEvent('keydown', {{
                                    'key': 'Enter',
                                    'code': 'Enter',
                                    'keyCode': 13,
                                    'which': 13,
                                    'bubbles': true
                                }}));
                                return true;
                            }}
                        }}
                        
                        return false;
                    }})();
                " in current tab of front window
                
                return loginResult
            end tell
            '''
            
            print("DEBUG - Oturum açma scripti çalıştırılıyor")
            result = subprocess.run(
                ["osascript", "-e", script], 
                capture_output=True, 
                text=True
            )
            
            login_success = "true" in result.stdout.lower()
            print(f"DEBUG - Oturum açma sonucu: {'başarılı' if login_success else 'başarısız'}")
            
            if login_success:
                return {
                    "success": True,
                    "message": "Oturum açma işlemi gerçekleştirildi"
                }
            else:
                return {
                    "success": False,
                    "message": "Oturum açma alanları bulunamadı"
                }
            
        except Exception as e:
            print(f"DEBUG - Oturum açma hatası: {e}")
            return {
                "success": False,
                "message": f"Oturum açma işlemi sırasında hata: {str(e)}"
            }
    
    def _execute_navigation_flow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Navigasyon akışını yürütür.
        
        Args:
            params: Navigasyon parametreleri
            
        Returns:
            İşlem sonucunu içeren sözlük
        """
        print(f"DEBUG - Navigasyon akışı başlatılıyor: {params}")
        
        url = params.get("url", "")
        selector = params.get("selector", "")
        
        try:
            if url:
                # Doğrudan URL'ye git
                success = self.open_url(url)
                return {
                    "success": success,
                    "message": f"URL'ye navigasyon: {url}"
                }
            elif selector:
                # CSS selektörü ile bir elemente tıkla
                script = f'''
                tell application "{self.default_browser}"
                    activate
                    delay 1
                    set clickResult to do JavaScript "
                        (function() {{
                            const element = document.querySelector('{selector}');
                            if (element) {{
                                element.click();
                                return true;
                            }}
                            return false;
                        }})();
                    " in current tab of front window
                    
                    return clickResult
                end tell
                '''
                
                result = subprocess.run(
                    ["osascript", "-e", script], 
                    capture_output=True, 
                    text=True
                )
                
                click_success = "true" in result.stdout.lower()
                return {
                    "success": click_success,
                    "message": f"Elemente tıklama: {selector}"
                }
            else:
                return {
                    "success": False,
                    "message": "Navigasyon için URL veya selektör belirtilmedi"
                }
                
        except Exception as e:
            print(f"DEBUG - Navigasyon hatası: {e}")
            return {
                "success": False,
                "message": f"Navigasyon işlemi sırasında hata: {str(e)}"
            }
    
    def _execute_scroll_flow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Kaydırma akışını yürütür.
        
        Args:
            params: Kaydırma parametreleri
            
        Returns:
            İşlem sonucunu içeren sözlük
        """
        print(f"DEBUG - Kaydırma akışı başlatılıyor: {params}")
        
        direction = params.get("direction", "down")
        amount = params.get("amount", "medium")
        selector = params.get("selector", "")
        
        try:
            # Kaydırma miktarını belirle (piksel)
            pixel_amount = 300  # Orta düzey kaydırma
            if amount == "small":
                pixel_amount = 100
            elif amount == "large":
                pixel_amount = 600
            elif isinstance(amount, int):
                pixel_amount = amount
            
            # Kaydırma yönünü belirle
            scroll_value = pixel_amount
            if direction == "up":
                scroll_value = -pixel_amount
            
            script = f'''
            tell application "{self.default_browser}"
                activate
                delay 1
                set scrollResult to do JavaScript "
                    (function() {{
                        // Belirli bir element varsa ona kaydır
                        if ('{selector}') {{
                            const element = document.querySelector('{selector}');
                            if (element) {{
                                element.scrollIntoView({{
                                    behavior: 'smooth',
                                    block: 'center'
                                }});
                                return true;
                            }}
                        }}
                        
                        // Belirli bir element yoksa sayfayı belirtilen miktarda kaydır
                        window.scrollBy({{
                            top: {scroll_value},
                            behavior: 'smooth'
                        }});
                        
                        return true;
                    }})();
                " in current tab of front window
                
                return scrollResult
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script], 
                capture_output=True, 
                text=True
            )
            
            scroll_success = "true" in result.stdout.lower()
            
            if selector and scroll_success:
                return {
                    "success": True,
                    "message": f"'{selector}' elementine kaydırıldı"
                }
            elif scroll_success:
                return {
                    "success": True,
                    "message": f"Sayfa {direction} yönünde {amount} miktar kaydırıldı"
                }
            else:
                return {
                    "success": False,
                    "message": "Kaydırma işlemi gerçekleştirilemedi"
                }
            
        except Exception as e:
            print(f"DEBUG - Kaydırma hatası: {e}")
            return {
                "success": False,
                "message": f"Kaydırma işlemi sırasında hata: {str(e)}"
            }
    
    def _execute_form_submission(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Form gönderme akışını yürütür.
        
        Args:
            params: Form parametreleri
            
        Returns:
            İşlem sonucunu içeren sözlük
        """
        print(f"DEBUG - Form gönderme akışı başlatılıyor: {params}")
        
        form_selector = params.get("form", "form")
        fields = params.get("fields", {})
        
        if not fields:
            return {
                "success": False,
                "message": "Form alanları belirtilmedi"
            }
        
        try:
            # Form alanlarını doldurma JavaScript kodu oluştur
            fields_js = ""
            for field_name, field_value in fields.items():
                fields_js += f"document.querySelector('input[name=\"{field_name}\"]').value = '{field_value}';\n"
            
            script = f'''
            tell application "{self.default_browser}"
                activate
                delay 1
                set formResult to do JavaScript "
                    (function() {{
                        // Form alanlarını doldur
                        try {{
                            {fields_js}
                            
                            // Formu bul ve gönder
                            const form = document.querySelector('{form_selector}');
                            if (form) {{
                                form.submit();
                                return true;
                            }} else {{
                                // Form bulunamadı, son input alanından sonra Enter tuşuna basarak dene
                                const fields = document.querySelectorAll('input, select, textarea');
                                if (fields.length > 0) {{
                                    const lastField = fields[fields.length - 1];
                                    lastField.dispatchEvent(new KeyboardEvent('keydown', {{
                                        'key': 'Enter',
                                        'code': 'Enter',
                                        'keyCode': 13,
                                        'which': 13,
                                        'bubbles': true
                                    }}));
                                    return true;
                                }}
                            }}
                        }} catch (e) {{
                            console.error('Form doldurma hatası:', e);
                            return false;
                        }}
                        
                        return false;
                    }})();
                " in current tab of front window
                
                return formResult
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script], 
                capture_output=True, 
                text=True
            )
            
            form_success = "true" in result.stdout.lower()
            
            if form_success:
                return {
                    "success": True,
                    "message": "Form başarıyla dolduruldu ve gönderildi"
                }
            else:
                return {
                    "success": False,
                    "message": "Form doldurulamadı veya gönderilemedi"
                }
            
        except Exception as e:
            print(f"DEBUG - Form gönderme hatası: {e}")
            return {
                "success": False,
                "message": f"Form işlemi sırasında hata: {str(e)}"
            }
    
    def _execute_form_fill(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Form doldurma akışını yürütür.
        
        Args:
            params: Form doldurma parametreleri
            
        Returns:
            İşlem sonucunu içeren sözlük
        """
        print(f"DEBUG - Form doldurma akışı başlatılıyor: {params}")
        
        fields = params.get("fields", {})
        
        if not fields:
            return {
                "success": False,
                "message": "Doldurulacak alanlar belirtilmedi"
            }
        
        try:
            # Form alanlarını doldurma JavaScript kodu oluştur
            fields_js = ""
            for field_name, field_value in fields.items():
                fields_js += f'''
                    try {{
                        // İsim ile ara
                        let field = document.querySelector('input[name="{field_name}"], textarea[name="{field_name}"], select[name="{field_name}"]');
                        
                        // İsim bulunamadıysa id ile ara
                        if (!field) {{
                            field = document.querySelector('#{field_name}, input[id="{field_name}"], textarea[id="{field_name}"], select[id="{field_name}"]');
                        }}
                        
                        // Placeholder ile ara
                        if (!field) {{
                            field = document.querySelector('input[placeholder*="{field_name}" i], textarea[placeholder*="{field_name}" i]');
                        }}
                        
                        // Label ile ara
                        if (!field) {{
                            const labels = document.querySelectorAll('label');
                            for (const label of labels) {{
                                if (label.textContent.toLowerCase().includes('{field_name.lower()}')) {{
                                    const id = label.getAttribute('for');
                                    if (id) {{
                                        field = document.getElementById(id);
                                        break;
                                    }}
                                }}
                            }}
                        }}
                        
                        if (field) {{
                            field.value = '{field_value}';
                            field.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            field.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            console.log('Alan dolduruldu:', '{field_name}');
                            filledFields++;
                        }}
                    }} catch (e) {{
                        console.error('Alan doldurma hatası:', e);
                    }}
                '''
            
            script = f'''
            tell application "{self.default_browser}"
                activate
                delay 1
                set fillResult to do JavaScript "
                    (function() {{
                        let filledFields = 0;
                        
                        // Form alanlarını doldur
                        {fields_js}
                        
                        return filledFields > 0;
                    }})();
                " in current tab of front window
                
                return fillResult
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script], 
                capture_output=True, 
                text=True
            )
            
            fill_success = "true" in result.stdout.lower()
            
            if fill_success:
                return {
                    "success": True,
                    "message": f"{len(fields)} alan başarıyla dolduruldu"
                }
            else:
                return {
                    "success": False,
                    "message": "Alanlar doldurulamadı"
                }
            
        except Exception as e:
            print(f"DEBUG - Form doldurma hatası: {e}")
            return {
                "success": False,
                "message": f"Form doldurma işlemi sırasında hata: {str(e)}"
            }
    
    def _execute_data_fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Veri çekme akışını yürütür.
        
        Args:
            params: Veri çekme parametreleri
            
        Returns:
            İşlem sonucunu içeren sözlük
        """
        print(f"DEBUG - Veri çekme akışı başlatılıyor: {params}")
        
        selector = params.get("selector", "")
        attribute = params.get("attribute", "textContent")
        
        if not selector:
            return {
                "success": False,
                "message": "Veri çekilecek element selektörü belirtilmedi"
            }
        
        try:
            script = f'''
            tell application "{self.default_browser}"
                activate
                delay 1
                set fetchResult to do JavaScript "
                    (function() {{
                        try {{
                            const elements = document.querySelectorAll('{selector}');
                            
                            if (elements.length === 0) {{
                                return JSON.stringify({{
                                    success: false,
                                    message: 'Belirtilen selektörle eşleşen element bulunamadı',
                                    data: null
                                }});
                            }}
                            
                            // Elementlerden veri topla
                            const results = [];
                            for (let i = 0; i < elements.length; i++) {{
                                const element = elements[i];
                                
                                // Belirtilen özelliği al
                                let value;
                                if ('{attribute}' === 'textContent' || '{attribute}' === 'innerText') {{
                                    value = element.textContent.trim();
                                }} else if ('{attribute}' === 'innerHTML') {{
                                    value = element.innerHTML;
                                }} else {{
                                    value = element.getAttribute('{attribute}');
                                }}
                                
                                results.push(value);
                            }}
                            
                            return JSON.stringify({{
                                success: true,
                                message: elements.length + ' element bulundu',
                                data: results
                            }});
                        }} catch (e) {{
                            return JSON.stringify({{
                                success: false,
                                message: 'Veri çekme hatası: ' + e.message,
                                data: null
                            }});
                        }}
                    }})();
                " in current tab of front window
                
                return fetchResult
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script], 
                capture_output=True, 
                text=True
            )
            
            # JSON sonucunu parse et
            try:
                result_json = json.loads(result.stdout.strip())
                return result_json
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": "Veri çekme sonucu parse edilemedi",
                    "data": None
                }
            
        except Exception as e:
            print(f"DEBUG - Veri çekme hatası: {e}")
            return {
                "success": False,
                "message": f"Veri çekme işlemi sırasında hata: {str(e)}",
                "data": None
            }
    
    def _execute_data_update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Veri güncelleme akışını yürütür.
        
        Args:
            params: Veri güncelleme parametreleri
            
        Returns:
            İşlem sonucunu içeren sözlük
        """
        print(f"DEBUG - Veri güncelleme akışı başlatılıyor: {params}")
        
        selector = params.get("selector", "")
        attribute = params.get("attribute", "textContent")
        value = params.get("value", "")
        
        if not selector or not value:
            return {
                "success": False,
                "message": "Element selektörü veya güncellenecek değer belirtilmedi"
            }
        
        try:
            script = f'''
            tell application "{self.default_browser}"
                activate
                delay 1
                set updateResult to do JavaScript "
                    (function() {{
                        try {{
                            const elements = document.querySelectorAll('{selector}');
                            
                            if (elements.length === 0) {{
                                return JSON.stringify({{
                                    success: false,
                                    message: 'Belirtilen selektörle eşleşen element bulunamadı',
                                    count: 0
                                }});
                            }}
                            
                            // Elementleri güncelle
                            let updatedCount = 0;
                            for (let i = 0; i < elements.length; i++) {{
                                const element = elements[i];
                                
                                if ('{attribute}' === 'textContent') {{
                                    element.textContent = '{value}';
                                    updatedCount++;
                                }} else if ('{attribute}' === 'innerHTML') {{
                                    element.innerHTML = '{value}';
                                    updatedCount++;
                                }} else if ('{attribute}' === 'value') {{
                                    element.value = '{value}';
                                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    updatedCount++;
                                }} else {{
                                    element.setAttribute('{attribute}', '{value}');
                                    updatedCount++;
                                }}
                            }}
                            
                            return JSON.stringify({{
                                success: updatedCount > 0,
                                message: updatedCount + ' element güncellendi',
                                count: updatedCount
                            }});
                        }} catch (e) {{
                            return JSON.stringify({{
                                success: false,
                                message: 'Veri güncelleme hatası: ' + e.message,
                                count: 0
                            }});
                        }}
                    }})();
                " in current tab of front window
                
                return updateResult
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script], 
                capture_output=True, 
                text=True
            )
            
            # JSON sonucunu parse et
            try:
                result_json = json.loads(result.stdout.strip())
                return result_json
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": "Veri güncelleme sonucu parse edilemedi",
                    "count": 0
                }
            
        except Exception as e:
            print(f"DEBUG - Veri güncelleme hatası: {e}")
            return {
                "success": False,
                "message": f"Veri güncelleme işlemi sırasında hata: {str(e)}",
                "count": 0
            }
    
    def execute_browser_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a browser action.
        
        Args:
            action: The action to perform (open, navigate, search, etc.)
            params: Parameters for the action
            
        Returns:
            Result dictionary
        """
        # Basit sorgu kontrolü - Browser gerekli mi yoksa gereksiz mi?
        is_browser_necessary = self._check_if_browser_necessary(action, params)
        
        if not is_browser_necessary:
            return {
                "success": False,
                "action": action,
                "message": "Bu işlem için tarayıcı açmaya gerek yok. Basit bilgi sorguları doğrudan cevaplanabilir."
            }
        
        # Browser navigation actions
        if action == "browser_open" or action == "browser_navigate":
            url = params.get("url", "")
            browser = params.get("browser", None)
            success = self.open_url(url, browser)
            
            return {
                "success": success,
                "action": action,
                "message": f"Opened URL: {url}" if success else f"Failed to open URL: {url}"
            }
        
        # General web shopping action
        elif action == "browser_shop_online":
            query = params.get("query", "")
            site = params.get("site", None)
            filters = params.get("filters", {})
            add_to_cart = params.get("add_to_cart", True)
            
            if not query:
                return {
                    "success": False,
                    "action": action,
                    "message": "No search query provided"
                }
                
            success = self.shop_online(query, site, filters, add_to_cart)
            
            return {
                "success": success,
                "action": action,
                "message": f"Searched and added to cart: {query}" if success else f"Failed to search or add to cart: {query}"
            }
        
        # Universal add to cart action - genişletilmiş sepete ekleme için yeni eylem
        elif action == "add_to_cart" or action == "browser_universal_add_to_cart":
            product = params.get("product", "")
            item_specs = params.get("item_specifications", {})
            site = params.get("site", None)
            
            if not product and item_specs:
                # Eğer ürün belirtilmemiş ama özellikler varsa, özellikleri birleştirerek ürün oluştur
                product = " ".join([f"{value}" for key, value in item_specs.items()])
            elif not product:
                return {
                    "success": False,
                    "action": action,
                    "message": "Sepete eklenecek ürün belirtilmedi"
                }
            
            # Özellikleri ürün açıklamasına ekle
            if item_specs:
                for key, value in item_specs.items():
                    if value not in product:
                        product += f" {value}"
            
            # Evrensel sepete ekleme metodunu çağır
            result = self.universal_add_to_cart(product, site)
            
            return {
                "success": result["success"],
                "action": action,
                "message": result["message"],
                "details": result
            }
        
        # Search actions
        elif action == "browser_search":
            query = params.get("query", "")
            site = params.get("site", None)
            engine = params.get("engine", None)
            
            if not query:
                return {
                    "success": False,
                    "action": action,
                    "message": "No search query provided"
                }
            
            if site:
                success = self.search_on_site(query, site)
                return {
                    "success": success,
                    "action": action,
                    "message": f"Searched for '{query}' on {site}" if success else f"Failed to search for '{query}' on {site}"
                }
            else:
                success = self.search_in_browser(query, engine)
                return {
                    "success": success,
                    "action": action,
                    "message": f"Searched for '{query}'" if success else f"Failed to search for '{query}'"
                }
        
        # Comprehensive search action
        elif action == "browser_comprehensive_search":
            query = params.get("query", "")
            search_engines = params.get("engines", None)
            sites = params.get("sites", None)
            max_results = params.get("max_results", 5)
            
            if not query:
                return {
                    "success": False,
                    "action": action,
                    "message": "No search query provided"
                }
            
            results = self.comprehensive_search(query, search_engines, sites, max_results)
            
            if results["success"]:
                return {
                    "success": True,
                    "action": action,
                    "message": f"Comprehensive search for '{query}' completed in {results['time_spent']} seconds. Examined {results['total_results_examined']} results across {len(results['engines_searched'])} engines and {len(results['sites_searched'])} sites.",
                    "data": results
                }
            else:
                return {
                    "success": False,
                    "action": action,
                    "message": f"Comprehensive search for '{query}' failed to find satisfactory results",
                    "data": results
                }
        
        # Multi-site search
        elif action == "browser_search_multiple":
            query = params.get("query", "")
            sites = params.get("sites", [])
            
            if not query or not sites:
                return {
                    "success": False,
                    "action": action,
                    "message": "No search query or sites provided"
                }
            
            result = self.search_multiple_sites(query, sites)
            
            if result["success"]:
                if result["found"]:
                    return {
                        "success": True,
                        "action": action,
                        "message": f"Found results for '{query}' on {result['final_site']} after searching {len(result['sites_searched'])} sites",
                        "data": result
                    }
                else:
                    return {
                        "success": True,
                        "action": action,
                        "message": f"Searched {len(result['sites_searched'])} sites for '{query}' but didn't find optimal results",
                        "data": result
                    }
            else:
                return {
                    "success": False,
                    "action": action,
                    "message": f"Failed to search for '{query}' across multiple sites",
                    "data": result
                }
        
        # Add to cart action
        elif action == "browser_add_to_cart":
            item = params.get("item", "")
            site = params.get("site", None)
            
            if not item:
                return {
                    "success": False,
                    "action": action,
                    "message": "No item specified for adding to cart"
                }
            
            success = self.add_to_cart(item, site)
            return {
                "success": success,
                "action": action,
                "message": f"Added to cart: {item}" if success else f"Failed to add to cart: {item}"
            }
        
        # Navigate to next search result
        elif action == "browser_next_result":
            success = self.navigate_to_next_search_result()
            return {
                "success": success,
                "action": action,
                "message": "Navigated to next search result" if success else "Failed to navigate to next search result"
            }
        
        # Click action
        elif action == "browser_click":
            element = params.get("element", "")
            
            if not element:
                return {
                    "success": False,
                    "action": action,
                    "message": "No element specified for clicking"
                }
            
            try:
                script = f'''
                tell application "{self.default_browser}"
                    activate
                    tell application "System Events"
                        click button "{element}" of front window
                    end tell
                end tell
                '''
                
                subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    check=True
                )
                
                return {
                    "success": True,
                    "action": action,
                    "message": f"Clicked element: {element}"
                }
            except:
                return {
                    "success": False,
                    "action": action,
                    "message": f"Failed to click element: {element}"
                }
        
        # Type action
        elif action == "browser_type":
            text = params.get("text", "")
            
            if not text:
                return {
                    "success": False,
                    "action": action,
                    "message": "No text provided to type"
                }
            
            try:
                script = f'''
                tell application "{self.default_browser}"
                    activate
                    tell application "System Events"
                        keystroke "{text}"
                    end tell
                end tell
                '''
                
                subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    check=True
                )
                
                return {
                    "success": True, 
                    "action": action,
                    "message": f"Typed text: {text}"
                }
            except:
                return {
                    "success": False,
                    "action": action,
                    "message": f"Failed to type text: {text}"
                }
        
        # Unknown action
        else:
            return {
                "success": False,
                "action": action,
                "message": f"Unknown browser action: {action}"
            }
    
    def _check_if_browser_necessary(self, action: str, params: Dict[str, Any]) -> bool:
        """
        Tarayıcı açmadan önce isteğin gerçekten tarayıcı gerektirip gerektirmediğini kontrol eder.
        
        Args:
            action: Gerçekleştirilecek eylem
            params: Eylemin parametreleri
            
        Returns:
            True eğer tarayıcı gerekli ise, False değilse
        """
        # Browser ile ilgili eylemler için hızlı kontrol
        browser_specific_actions = [
            "browser_open", "browser_navigate", "browser_shop_online", 
            "browser_search", "browser_comprehensive_search", "browser_search_multiple",
            "browser_add_to_cart", "browser_next_result", "browser_click", "browser_type",
            "add_to_cart", "browser_universal_add_to_cart"
        ]
        
        # Basit bilgi sorguları için kontroller
        if action == "system_info":
            # Sistem bilgileri sorgulanıyor, tarayıcı gerekmez
            return False
            
        # Tarayıcı eylemlerinde sorgu içeriğine bakıp gerçekten tarayıcıya ihtiyaç var mı anlayalım
        if action in browser_specific_actions:
            query = params.get("query", "")
            url = params.get("url", "")
            
            # Eğer URL belirtilmişse, muhtemelen tarayıcı gereklidir
            if url:
                return True
                
            # Basit kişisel soru kalıpları - bunlar genellikle tarayıcı gerektirmez
            personal_query_patterns = [
                "kendin", "kendini", "tanıt", "merhaba", "selam", "nasılsın", 
                "kimsin", "neler yapabilirsin", "özellikler", "yetenekler",
                "yardım et", "ne yapabilirsin", "capabilities"
            ]
            
            # Sorgu içeriğinde yukarıdaki kelimeler/kalıplar varsa ve sorgu kısa ise muhtemelen tarayıcı gerektirmez
            if query and len(query.split()) < 10:  # Kısa sorgular
                query_lower = query.lower()
                for pattern in personal_query_patterns:
                    if pattern in query_lower:
                        print(f"DEBUG - Sorgu '{query}' tarayıcı açmayı gerektirmiyor")
                        return False
        
        # Web araması, alışveriş vs. için tarayıcı gerekli
        if action in browser_specific_actions:
            # Araştırma amaçlı tarayıcı gerekip gerekmediğini kontrol et
            query = params.get("query", "")
            if query:
                research_keywords = [
                    "araştır", "bul", "nedir", "nasıl", "hangisi", "ne zaman", "nerede",
                    "research", "find", "what is", "how to", "which", "when", "where",
                    "arama yap", "search", "look up", "check"
                ]
                
                query_lower = query.lower()
                for keyword in research_keywords:
                    if keyword in query_lower:
                        # Araştırma amaçlı sorgu, tarayıcı gerekli
                        print(f"DEBUG - Araştırma sorgusu '{query}' tarayıcı gerektirir")
                        return True
        
        # Varsayılan olarak tarayıcı eylemleri için tarayıcı gerekir
        return action in browser_specific_actions
        
    def _optimize_js_execution(self, script: str) -> str:
        """
        JavaScript yürütmesini optimize eder ve performansı artırır.
        
        Args:
            script: Orijinal JavaScript kodu
            
        Returns:
            Optimize edilmiş JavaScript kodu
        """
        # 1. Gereksiz bekleme sürelerini azalt (delay değerlerini düşür)
        script = re.sub(r'delay (\d+(\.\d+)?)', lambda m: f'delay {float(m.group(1))*0.7}', script)
        
        # 2. JavaScript'te performans optimizasyonları yap
        if "do JavaScript" in script:
            # DOM seçicileri için daha verimli yöntemler kullan
            script = script.replace('document.querySelectorAll', 'document.getElementsBy')
            
            # forEach yerine for döngüsü kullan (daha hızlı)
            script = script.replace('.forEach(', '.map(')
            
            # Timeout değerlerini düşür
            script = re.sub(r'setTimeout\(\s*\(\)\s*=>\s*{(.*?)}\s*,\s*(\d+)\s*\)', 
                          lambda m: f'setTimeout(() => {{{m.group(1)}}}, {int(int(m.group(2))*0.7)})', 
                          script)
        
        return script
    
    def shop_online(self, query: str, site: str = None, filters: Dict[str, str] = None, add_to_cart: bool = True) -> bool:
        """
        Search for products and add them to cart on any e-commerce or shopping website globally.
        
        Args:
            query: Product search query
            site: Website domain (e.g., "amazon.com", "ebay.com", etc.)
            filters: Product filters (color, price range, brand, etc.)
            add_to_cart: Whether to add the product to cart
            
        Returns:
            True if successful, False otherwise
        """
        print(f"DEBUG - Alışveriş başlatılıyor: ürün={query}, site={site}")
        
        # If site is provided, search on that site
        if site:
            # Try to construct a search URL based on common patterns
            search_url = self._get_search_url(site, query)
            
            if search_url:
                # Open the search URL
                print(f"DEBUG - Arama URL'si kullanılıyor: {search_url}")
                success = self.open_url(search_url)
                if not success:
                    print("DEBUG - URL açma başarısız oldu")
                    return False
            else:
                # If we don't have a specific search URL pattern, open the site and search manually
                site_url = f"https://{site}" if not site.startswith(("http://", "https://")) else site
                print(f"DEBUG - Site doğrudan açılıyor: {site_url}")
                success = self.open_url(site_url)
                if not success:
                    print("DEBUG - Site açma başarısız oldu")
                    return False
                
                # Wait for the page to load
                print("DEBUG - Sayfa yüklenmesi için bekleniyor (3 saniye)")
                time.sleep(3)
                
                # Try to search on the site
                print(f"DEBUG - Site içi arama yapılıyor: {query}")
                success = self._search_on_loaded_site(query)
                if not success:
                    print("DEBUG - Site içi arama başarısız oldu")
                    return False
        else:
            # If no specific site is provided, default to a general search
            print(f"DEBUG - Genel arama yapılıyor: {query}")
            success = self.search_in_browser(query, "google")
            if not success:
                print("DEBUG - Genel arama başarısız oldu")
                return False
        
        # Wait for search results to load
        print("DEBUG - Arama sonuçlarının yüklenmesi için bekleniyor (5 saniye)")
        time.sleep(5)
        
        # Apply filters if provided
        if filters:
            print(f"DEBUG - Filtreler uygulanıyor: {filters}")
            self._apply_universal_filters(filters)
            # Wait for filters to apply
            print("DEBUG - Filtrelerin uygulanması için bekleniyor (3 saniye)")
            time.sleep(3)
        
        # Select first product if we want to add to cart
        if add_to_cart:
            # Click the first product
            print("DEBUG - İlk ürüne tıklanıyor")
            success = self._click_first_product_universal()
            if not success:
                print("DEBUG - Ürüne tıklama başarısız oldu")
                return False
            
            # Wait for product page to load
            print("DEBUG - Ürün sayfasının yüklenmesi için bekleniyor (5 saniye)")
            time.sleep(5)
            
            # Add to cart
            print("DEBUG - Sepete ekleme işlemi başlatılıyor")
            cart_success = self._add_to_cart_universal()
            print(f"DEBUG - Sepete ekleme sonucu: {'başarılı' if cart_success else 'başarısız'}")
            return cart_success
        
        print("DEBUG - Alışveriş işlemi tamamlandı")
        return True
    
    def _get_search_url(self, site: str, query: str) -> Optional[str]:
        """
        Get a search URL for a given site and query.
        
        Args:
            site: Website domain
            query: Search query
            
        Returns:
            Search URL or None if not found
        """
        # Common search URL patterns for popular e-commerce sites worldwide
        site = site.lower()
        