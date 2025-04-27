#!/usr/bin/env python3
"""
AI Helper - A local LLM-powered assistant that can interact with your macOS system

This is the main entry point for the AI Helper application. It handles command-line
arguments, initializes the LLM, and manages the interaction loop.
"""

import os
import sys
import argparse
from pathlib import Path
import platform

# Local imports
from model_loader import ModelLoader
from inference import LLMInference
from manager import PermissionManager
from terminal import TerminalUI
from browser import BrowserController
from apps import AppController
from files import FileController
from screen import ScreenController

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="AI Helper - Run LLM locally and interact with your macOS system"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        required=True,
        help="Path to the LLM model file (GGUF format)"
    )
    parser.add_argument(
        "--backend",
        type=str,
        choices=["auto", "ollama", "lmstudio", "lmstudio_sdk", "lmstudio_openai"],
        default="auto",
        help="LLM backend to use (auto, ollama, lmstudio, lmstudio_sdk, lmstudio_openai)"
    )
    parser.add_argument(
        "--context-length",
        type=int,
        default=4096,
        help="Context length for the model (default: 4096)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Temperature for text generation (default: 0.7)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    return parser.parse_args()

# LLM hata işleyici sınıfı ekle
class LLMErrorHandler:
    """LLM hatalarını yöneten yardımcı sınıf."""
    
    def __init__(self, max_retries=3):
        """
        Hata işleyici başlat.
        
        Args:
            max_retries: Maksimum yeniden deneme sayısı
        """
        self.max_retries = max_retries
        self.retry_count = 0
        self.last_error = None
    
    def should_retry(self, error):
        """
        Hatanın yeniden denemeye değer olup olmadığını kontrol eder.
        
        Args:
            error: Oluşan hata
            
        Returns:
            Yeniden deneme yapılıp yapılmayacağı
        """
        self.last_error = error
        self.retry_count += 1
        return self.retry_count <= self.max_retries
    
    def reset(self):
        """Sayaçları sıfırla."""
        self.retry_count = 0
        self.last_error = None
    
    def get_error_prompt(self):
        """
        LLM'e hatayı açıklayan prompt oluşturur.
        
        Returns:
            Hata ile ilgili prompt
        """
        return f"""
        Önceki yanıtınızı işlerken bir hata oluştu: {str(self.last_error)}
        
        İstediğiniz eylemi gerçekleştirirken sorun yaşadım. Lütfen yanıtınızı düzeltip tekrar deneyeyim.
        
        Lütfen aşağıdaki kurallara dikkat ederek yanıtınızı yeniden düzenleyin:
        
        1. JSON formatının doğru olduğundan emin olun:
           • Tüm anahtarlar ve string değerler çift tırnak (") içinde olmalı
           • JSON'unuz mutlaka şu formatta olmalı: {{"action": "eylem_adı", "params": {{"parametre1": "değer1"}}}}
           • JSON bloğunu ```json ve ``` işaretleri arasına yazın
        
        2. Desteklenen eylem türlerini kullanın:
           • browser_open, browser_search: Tarayıcı işlemleri
           • file_read, file_write, file_create, file_delete: Dosya işlemleri
           • app_open, app_close: Uygulama işlemleri
           • terminal_execute, command_run: Komut çalıştırma işlemleri
           • folder_create: Klasör oluşturma
        
        3. Her eylem için gerekli tüm parametreleri ekleyin (örnekler):
           • browser_open için: {{"action": "browser_open", "params": {{"url": "https://example.com"}}}}
           • file_read için: {{"action": "file_read", "params": {{"path": "/dosya/yolu.txt"}}}}
           • terminal_execute için: {{"action": "terminal_execute", "params": {{"command": "ls -la"}}}}
        
        Lütfen tekrar deneyin ve istediğiniz eylemi doğru JSON formatıyla belirtin.
        """

def main():
    """Main entry point for the application."""
    args = parse_arguments()
    
    # Check if model file exists
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"Error: Model file not found: {args.model}")
        sys.exit(1)
    
    # Initialize components
    ui = TerminalUI(verbose=args.verbose)
    ui.display_welcome()
    
    permission_manager = PermissionManager()
    
    # Initialize system controllers
    browser_controller = BrowserController()
    app_controller = AppController()
    file_controller = FileController()
    screen_controller = ScreenController()
    
    # Initialize error handler
    error_handler = LLMErrorHandler(max_retries=3)
    
    # Load the model
    ui.display_status("Loading LLM model...")
    try:
        model_loader = ModelLoader(
            model_path=str(model_path),
            context_length=args.context_length,
            temperature=args.temperature
        )
        llm = model_loader.load_model()
        inference = LLMInference(llm)
        ui.display_status("Model loaded successfully!")
    except Exception as e:
        ui.display_error(f"Failed to load model: {str(e)}")
        sys.exit(1)
    
    # Main interaction loop
    ui.display_status("AI Helper is ready! Type your requests or 'exit' to quit.")
    
    while True:
        # Get user input
        user_input = ui.get_input()
        
        if user_input.lower() in ('exit', 'quit'):
            ui.display_status("Exiting AI Helper. Goodbye!")
            break
        
        # Process with LLM
        ui.display_status("Processing your request...")
        
        # Hata işleyici sıfırla
        error_handler.reset()
        current_input = user_input
        
        # Retry loop
        while True:
            try:
                response = inference.process_input(current_input)
                
                # Extract action requests from response
                actions = extract_actions_from_response(response)
                
                # Execute each action
                action_success = True
                action_results = []
                
                for action in actions:
                    action_type = action.get('type')
                    if not action_type and 'action' in action:
                        action_type = action.get('action')
                        
                    action_params = action.get('params', {})
                    
                    # İzin kontrolünü atla, doğrudan eylemi çalıştır
                    ui.display_status(f"Executing: {action_type}")
                    
                    # Eylemi çalıştır
                    result = execute_action(action_type, action_params, 
                                          browser_controller, app_controller, 
                                          file_controller, screen_controller)
                    action_results.append(result)
                    
                    if result and result.get('success', False):
                        ui.display_result(f"Action completed: {result.get('message', '')}")
                        
                        # Terminal çıktılarını göster
                        if action_type in ["terminal_execute", "command_run"] and "stdout" in result:
                            stdout = result.get("stdout", "").strip()
                            if stdout:
                                ui.display_response(f"Komut çıktısı:\n```\n{stdout}\n```")
                    else:
                        ui.display_error(f"Failed to execute action: {action_type}")
                        action_success = False
                
                # Eğer tüm eylemler başarılı olduysa döngüden çık
                if action_success or not actions:
                    break
                
                # Eylem başarısız olursa, yeniden denemeye karar ver
                if error_handler.should_retry("Eylem yürütme hatası"):
                    error_prompt = error_handler.get_error_prompt()
                    
                    # Kullanıcıya tekrar denediğimizi göster
                    ui.display_retry_attempt(error_handler.retry_count, "Eylem yürütme hatası")
                    
                    current_input = error_prompt
                    continue
                else:
                    # Maksimum deneme sayısına ulaşıldı
                    ui.display_error(f"Maksimum deneme sayısına ulaşıldı. Eylem başarısız oldu.")
                    break
                
            except Exception as e:
                # LLM ile ilgili herhangi bir hata olursa
                if error_handler.should_retry(e):
                    error_prompt = error_handler.get_error_prompt()
                    
                    # Kullanıcıya tekrar denediğimizi göster
                    ui.display_retry_attempt(error_handler.retry_count, str(e))
                    
                    current_input = error_prompt
                    continue
                else:
                    # Maksimum deneme sayısına ulaşıldı
                    ui.display_error(f"Error processing request: {str(e)}")
                    break
        
        # Display final response
        ui.display_response(response)

def extract_actions_from_response(response):
    """
    LLM yanıtından eylem isteklerini çıkar.
    
    Args:
        response: LLM'den gelen yanıt
    
    Returns:
        List of action dictionaries
    """
    actions = []
    
    try:
        # JSON formatını çıkarmak için çeşitli yöntemler dene
        actions = extract_json_with_multiple_methods(response)
        
        # Hiçbir eylem çıkarılamadıysa, son çare olarak manuel ayıklama yap
        if not actions:
            actions = extract_actions_manually(response)
        
        # Sonuçları göster
        if actions:
            print(f"DEBUG - Toplam {len(actions)} eylem çıkarıldı")
        else:
            print("DEBUG - Hiç eylem çıkarılamadı!")
            
    except Exception as e:
        print(f"DEBUG - Eylem çıkarma hatası: {str(e)}")
    
    return actions

def extract_json_with_multiple_methods(response):
    """Çeşitli yöntemlerle JSON'ları çıkarmayı dener."""
    import re
    import json
    actions = []
    
    print("DEBUG - Çok satırlı JSON taraması başlıyor...")
    # 1. Çok satırlı JSON bloklarını bul (```json ... ``` formatı)
    json_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', response)
    for block in json_blocks:
        try:
            # Birden fazla JSON objesi olabilir, ayır
            block = block.strip()
            # JSON objesinin başlangıç ve bitişini bul
            json_objects = re.findall(r'({[\s\S]*?})', block)
            
            for json_obj in json_objects:
                try:
                    action_data = json.loads(json_obj)
                    if is_valid_action(action_data):
                        actions.append(normalize_action(action_data))
                except json.JSONDecodeError as e:
                    print(f"DEBUG - JSON kod bloğu ayrıştırma hatası: {str(e)}")
        except Exception as e:
            print(f"DEBUG - Kod bloğu işleme hatası: {str(e)}")
    
    # 2. Açık JSON formatını ara (```'dan bağımsız)
    if not actions:
        print("DEBUG - Açık JSON formatı taraması...")
        # Çoklu JSON obje formatını destekle
        json_objects = re.findall(r'({[\s\S]*?})', response)
        for json_obj in json_objects:
            try:
                # JSON'ı temizle - whitespace ve satır sonlarını normalize et
                cleaned = json_obj.strip().replace('\n', ' ')
                action_data = json.loads(cleaned)
                if is_valid_action(action_data):
                    actions.append(normalize_action(action_data))
            except json.JSONDecodeError:
                # Bu bir geçerli JSON değil, ignore
                pass
    
    # 3. Satır tabanlı JSON arama (alternatif)
    if not actions:
        print("DEBUG - Satır tabanlı JSON arama...")
        collecting = False
        current_json = ""
        bracket_count = 0
        
        for line in response.split('\n'):
            line = line.strip()
            
            # JSON başlangıcı ara
            if '{' in line and not collecting:
                collecting = True
                current_json = line
                bracket_count = line.count('{') - line.count('}')
                continue
            
            # JSON toplama devam ediyor
            if collecting:
                current_json += line
                bracket_count += line.count('{') - line.count('}')
                
                # Parantezler eşleşti mi kontrol et
                if bracket_count == 0:
                    # JSON tamamlandı, ayrıştırmayı dene
                    try:
                        # İlk { ve son } arasını al
                        start = current_json.find('{')
                        end = current_json.rfind('}') + 1
                        if start >= 0 and end > start:
                            json_str = current_json[start:end]
                            action_data = json.loads(json_str)
                            if is_valid_action(action_data):
                                actions.append(normalize_action(action_data))
                    except json.JSONDecodeError:
                        # JSON ayrıştırılamadı, devam et
                        pass
                    
                    # Yeni JSON için hazırlan
                    collecting = False
                    current_json = ""
                    
    return actions

def extract_actions_manually(response):
    """Eylem adı ve parametreleri manuel olarak çıkarır."""
    import re
    import json
    actions = []
    
    # Bilinen eylem adlarını ara
    action_patterns = [
        (r'create_folder|folder_create|mkdir|createfolder|klasör_oluştur', 'folder_create'),
        (r'create_file|file_create|touch|createfile|dosya_oluştur', 'file_create'),
        (r'delete_file|file_delete|rm|deletefile|dosya_sil', 'file_delete'),
        (r'read_file|file_read|cat|readfile|dosya_oku', 'file_read'),
        (r'run_command|command_run|exec|runcommand|komut_çalıştır', 'command_run'),
        (r'browser_open|open_url|browser_navigate|tarayıcı_aç|url_aç', 'browser_open'),
        (r'browser_search|search_on_site|tarayıcıda_ara|site_arama|google\'da ara|search', 'browser_search'),
        (r'browser_shop_online|online_alışveriş|alışveriş_yap|satın_al', 'browser_shop_online'),
        (r'add_to_cart|sepete_ekle|satın_al|sepet', 'browser_universal_add_to_cart'),
        (r'browser_comprehensive_search|kapsamlı_arama|detaylı_arama', 'browser_comprehensive_search')
    ]
    
    actions_found = []
    # Her bir eylem tipini ara
    for pattern, action_type in action_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            actions_found.append(action_type)
    
    print(f"DEBUG - Manuel olarak bulunan eylemler: {actions_found}")
    
    # Her bir bulunan eylem için parametreleri çıkarmayı dene
    for action_type in actions_found:
        # Klasör oluşturma
        if action_type == 'folder_create':
            # Path ve folder_name parametrelerini ara
            path_match = re.search(r'"path":\s*"([^"]+)"', response)
            folder_name_match = re.search(r'"folder_name":\s*"([^"]+)"', response)
            
            if path_match:
                path = path_match.group(1)
                folder_name = folder_name_match.group(1) if folder_name_match else ""
                
                actions.append({
                    "action": "folder_create",
                    "params": {
                        "path": path,
                        "folder_name": folder_name
                    }
                })
        
        # Dosya oluşturma
        elif action_type == 'file_create':
            # Path, file_name, content ve extension parametrelerini ara
            path_match = re.search(r'"path":\s*"([^"]+)"', response)
            file_name_match = re.search(r'"file_name":\s*"([^"]+)"', response)
            content_match = re.search(r'"(?:file_)?content":\s*"([^"]+)"', response)
            extension_match = re.search(r'"extension":\s*"([^"]+)"', response)
            
            if path_match or file_name_match:
                # Parametreleri topla
                params = {}
                if path_match:
                    params["path"] = path_match.group(1)
                if file_name_match:
                    params["file_name"] = file_name_match.group(1)
                if content_match:
                    params["content"] = content_match.group(1)
                if extension_match:
                    params["extension"] = extension_match.group(1)
                
                # İçerik yoksa dosya türüne göre varsayılan içerik belirle
                path = params.get("path", "")
                if "content" not in params and path:
                    path_lower = path.lower()
                    if ".txt" in path_lower:
                        params["content"] = "Bu bir metin dosyasıdır."
                    elif ".py" in path_lower:
                        params["content"] = "# Bu bir Python dosyasıdır\nprint('Merhaba, Dünya!')"
                
                actions.append({
                    "action": "file_create",
                    "params": params
                })
        
        # Terminal komutu çalıştırma
        elif action_type == 'command_run':
            # Komut parametresini ara
            command_match = re.search(r'"command":\s*"([^"]+)"', response)
            
            if command_match:
                command = command_match.group(1)
            else:
                # Metinden komut bulmaya çalış
                command_search = re.search(r'(?:çalıştır|execute|run)(?:\s+command)?[:\s]+[\"\']?([^\"\'\.\?]+)[\"\'\.\?]?', response, re.IGNORECASE)
                if command_search:
                    command = command_search.group(1).strip()
                else:
                    continue  # Komut bulunamadı, eylemi atla
            
            actions.append({
                "action": "terminal_execute",
                "params": {
                    "command": command
                }
            })

        # Tarayıcı açma eylemi 
        elif action_type == 'browser_open':
            # URL parametresini ara
            url_match = re.search(r'"(?:url|link|adres|site)":\s*"([^"]+)"', response)
            browser_match = re.search(r'"(?:browser|tarayıcı)":\s*"([^"]+)"', response)
            
            # Metinden URL bulmaya çalış
            if not url_match:
                urls = re.findall(r'https?://[^\s"\']+', response)
                if urls:
                    url = urls[0]
                else:
                    # Basit URL tahminleri
                    common_sites = ["google.com", "apple.com", "amazon.com", "youtube.com"]
                    for site in common_sites:
                        if site in response.lower():
                            url = f"https://www.{site}"
                            break
                    else:
                        continue  # Hiçbir URL bulunamadı, bu eylemi atla
            else:
                url = url_match.group(1)
            
            # Browser parametresi
            browser = browser_match.group(1) if browser_match else None
            
            actions.append({
                "action": "browser_open",
                "params": {
                    "url": url,
                    "browser": browser
                }
            })
        
        # Tarayıcıda arama eylemi
        elif action_type == 'browser_search':
            # Query ve site parametrelerini ara
            query_match = re.search(r'"(?:query|search|arama|sorgula)":\s*"([^"]+)"', response)
            site_match = re.search(r'"(?:site|website|sayfa)":\s*"([^"]+)"', response)
            engine_match = re.search(r'"(?:engine|motor|search_engine)":\s*"([^"]+)"', response)
            
            # Metinden sorgu bulmaya çalış
            if not query_match:
                # "ara", "bul", "search" gibi kelimelerin ardından gelen metni bul
                text_search = re.search(r'(?:ara|bul|search)(?:\s+for)?[:\s]+[\"\']?([^\"\'\.\?]+)[\"\'\.\?]?', response, re.IGNORECASE)
                if text_search:
                    query = text_search.group(1).strip()
                else:
                    # Son çare: iphone, macbook gibi ürün adlarını bul
                    product_match = re.search(r'(?:iphone|macbook|samsung|nokia|xbox|playstation|tv|laptop)(?:\s+\w+){0,3}', response, re.IGNORECASE)
                    if product_match:
                        query = product_match.group(0)
                    else:
                        continue  # Sorgu bulunamadı, eylemi atla
            else:
                query = query_match.group(1)
            
            params = {"query": query}
            
            if site_match:
                params["site"] = site_match.group(1)
            
            if engine_match:
                params["engine"] = engine_match.group(1)
            
            actions.append({
                "action": "browser_search",
                "params": params
            })
            
        # Online alışveriş eylemi
        elif action_type == 'browser_shop_online':
            # Query, site, filters parametrelerini ara
            query_match = re.search(r'"(?:query|product|ürün|item)":\s*"([^"]+)"', response)
            site_match = re.search(r'"(?:site|website|sayfa)":\s*"([^"]+)"', response)
            
            # Metinden ürün adını bulmaya çalış
            if not query_match:
                # Ürün adı tahmin et
                product_match = re.search(r'(?:iphone|macbook|samsung|nokia|xbox|playstation|tv|laptop)(?:\s+\w+){0,3}', response, re.IGNORECASE)
                if product_match:
                    query = product_match.group(0)
                else:
                    continue  # Ürün bulunamadı, eylemi atla
            else:
                query = query_match.group(1)
            
            params = {"query": query}
            
            if site_match:
                params["site"] = site_match.group(1)
            else:
                # Site tahmin et
                for site in ["amazon", "apple", "bestbuy", "walmart", "ebay"]:
                    if site in response.lower():
                        params["site"] = f"{site}.com"
                        break
            
            # Filtreleri bul
            filter_matches = re.findall(r'"([^"]+)":\s*"([^"]+)"', response)
            filters = {}
            for key, value in filter_matches:
                if key.lower() in ["price", "fiyat", "color", "renk", "size", "boyut"]:
                    filters[key] = value
            
            if filters:
                params["filters"] = filters
            
            actions.append({
                "action": "browser_shop_online",
                "params": params
            })
            
        # Sepete ekleme eylemi
        elif action_type == 'browser_universal_add_to_cart':
            # Product ve site parametrelerini ara
            product_match = re.search(r'"(?:product|ürün|item)":\s*"([^"]+)"', response)
            site_match = re.search(r'"(?:site|website|sayfa)":\s*"([^"]+)"', response)
            
            # Metinden ürün adını bulmaya çalış
            if not product_match:
                # Ürün adı tahmin et
                product_search = re.search(r'(?:sepete ekle|add to cart|satın al|buy)(?:[:\s]+[\"\']?([^\"\'\.\?]+)[\"\'\.\?])?', response, re.IGNORECASE)
                if product_search and product_search.group(1):
                    product = product_search.group(1).strip()
                else:
                    product_match = re.search(r'(?:iphone|macbook|samsung|nokia|xbox|playstation|tv|laptop)(?:\s+\w+){0,3}', response, re.IGNORECASE)
                    if product_match:
                        product = product_match.group(0)
                    else:
                        continue  # Ürün bulunamadı, eylemi atla
            else:
                product = product_match.group(1)
            
            params = {"product": product}
            
            if site_match:
                params["site"] = site_match.group(1)
            
            actions.append({
                "action": "browser_universal_add_to_cart",
                "params": params
            })
            
        # Kapsamlı arama eylemi
        elif action_type == 'browser_comprehensive_search':
            # Query ve diğer parametreleri ara
            query_match = re.search(r'"(?:query|search|arama|sorgula)":\s*"([^"]+)"', response)
            
            # Metinden sorgu bulmaya çalış
            if not query_match:
                # "kapsamlı ara", "detaylı ara" gibi kelimelerin ardından gelen metni bul
                text_search = re.search(r'(?:kapsamlı ara|detaylı ara|comprehensive search)(?:\s+for)?[:\s]+[\"\']?([^\"\'\.\?]+)[\"\'\.\?]?', response, re.IGNORECASE)
                if text_search:
                    query = text_search.group(1).strip()
                else:
                    # Son çare: ürün, konu, vb. adları bul
                    product_match = re.search(r'(?:iphone|macbook|samsung|nokia|xbox|playstation|tv|laptop)(?:\s+\w+){0,3}', response, re.IGNORECASE)
                    if product_match:
                        query = product_match.group(0)
                    else:
                        continue  # Sorgu bulunamadı, eylemi atla
            else:
                query = query_match.group(1)
            
            params = {"query": query}
            
            # Diğer parametreleri ara
            engines_match = re.search(r'"(?:engines|search_engines|motors)":\s*(\[[^\]]+\])', response)
            sites_match = re.search(r'"(?:sites|websites|sayfalar)":\s*(\[[^\]]+\])', response)
            max_results_match = re.search(r'"(?:max_results|limit|sonuç_limiti)":\s*(\d+)', response)
            
            if engines_match:
                try:
                    engines = json.loads(engines_match.group(1))
                    params["engines"] = engines
                except:
                    pass
            
            if sites_match:
                try:
                    sites = json.loads(sites_match.group(1))
                    params["sites"] = sites
                except:
                    pass
            
            if max_results_match:
                try:
                    max_results = int(max_results_match.group(1))
                    params["max_results"] = max_results
                except:
                    pass
            
            actions.append({
                "action": "browser_comprehensive_search",
                "params": params
            })
    
    return actions

def is_valid_action(action_data):
    """Bir verinin geçerli bir eylem olup olmadığını kontrol eder."""
    # action veya type anahtarı var mı kontrol et
    has_action_key = 'action' in action_data or 'type' in action_data
    
    # params anahtarı var mı ve içeriği dict mi kontrol et
    has_params = 'params' in action_data and isinstance(action_data['params'], dict)
    
    if has_action_key:
        action_name = action_data.get('action', action_data.get('type', ''))
        print(f"DEBUG - Eylem bulundu: {action_name}")
        return True
    
    return False

def normalize_action(action_data):
    """Eylem verilerini standart formata dönüştürür."""
    # Eylem adını normalize et
    action_type = None
    if 'action' in action_data:
        action_type = action_data['action']
    elif 'type' in action_data:
        action_type = action_data['type']
    
    # Eylem adını eşleştir
    action_type_mapping = {
        # Klasör işlemleri
        "create_folder": "folder_create",
        "createfolder": "folder_create",
        "mkdir": "folder_create",
        "klasör_oluştur": "folder_create",
        "yeni_klasör": "folder_create",
        
        # Dosya işlemleri
        "create_file": "file_create",
        "createfile": "file_create",
        "touch": "file_create",
        "dosya_oluştur": "file_create",
        "yeni_dosya": "file_create",
        
        # Silme işlemleri
        "delete_file": "file_delete",
        "deletefile": "file_delete",
        "rm": "file_delete",
        "dosya_sil": "file_delete",
        
        # Okuma işlemleri
        "read_file": "file_read",
        "readfile": "file_read",
        "cat": "file_read",
        "dosya_oku": "file_read",
        
        # Dosya yazma işlemleri
        "file_write": "file_write",
        "write_file": "file_write",
        "write": "file_write",
        "dosya_yaz": "file_write",
        
        # Terminal komut çalıştırma işlemleri
        "terminal_execute": "terminal_execute",
        "terminal_run": "terminal_execute",
        "command_run": "terminal_execute",
        "run_command": "terminal_execute",
        "exec": "terminal_execute",
        "komut_çalıştır": "terminal_execute",
        
        # Tarayıcı işlemleri
        "browser_search": "browser_search",
        "tarayıcıda_ara": "browser_search",
        "search_on_site": "browser_search",
        "site_arama": "browser_search",
        
        "browser_shop_online": "browser_shop_online",
        "online_alışveriş": "browser_shop_online",
        
        "add_to_cart": "browser_universal_add_to_cart",
        "sepete_ekle": "browser_universal_add_to_cart",
        
        "browser_comprehensive_search": "browser_comprehensive_search",
        "kapsamlı_arama": "browser_comprehensive_search"
    }
    
    # Eylem adını normalize et
    normalized_action = action_type_mapping.get(action_type, action_type)
    
    # Parametreleri kopyala ve normalize et
    params = action_data.get('params', {}).copy()
    
    # Path parametrelerindeki kullanıcı adını değiştir
    if 'path' in params:
        user_name = os.environ.get("USER", "")
        params['path'] = params['path'].replace("<kullanıcı_adı>", user_name)
        params['path'] = params['path'].replace("<username>", user_name)
        params['path'] = params['path'].replace("<user>", user_name)
        params['path'] = params['path'].replace("~", os.path.expanduser("~"))
    
    # Normalize edilmiş eylem verisi oluştur
    normalized_data = {
        "action": normalized_action,
        "params": params
    }
    
    print(f"DEBUG - Normalize edilmiş eylem: {normalized_action}, parametreler: {params}")
    return normalized_data

def execute_action(action_type, params, browser_controller, app_controller, file_controller, screen_controller):
    """
    Execute the requested action using the appropriate controller.
    
    Args:
        action_type: Type of action to perform
        params: Parameters for the action
        browser_controller: Browser controller instance
        app_controller: App controller instance
        file_controller: File controller instance
        screen_controller: Screen controller instance
        
    Returns:
        Result dictionary
    """
    # Eylem adı eşleştirmelerini düzelt
    action_type_mapping = {
        # Klasör işlemleri
        "create_folder": "folder_create",
        "createfolder": "folder_create",
        "mkdir": "folder_create",
        "klasör_oluştur": "folder_create",
        "yeni_klasör": "folder_create",
        
        # Dosya işlemleri
        "create_file": "file_create",
        "createfile": "file_create",
        "touch": "file_create",
        "dosya_oluştur": "file_create",
        "yeni_dosya": "file_create",
        
        # Silme işlemleri
        "delete_file": "file_delete",
        "deletefile": "file_delete",
        "rm": "file_delete",
        "dosya_sil": "file_delete",
        
        # Okuma işlemleri
        "read_file": "file_read",
        "readfile": "file_read",
        "cat": "file_read",
        "dosya_oku": "file_read",
        
        # Dosya yazma işlemleri
        "file_write": "file_write",
        "write_file": "file_write",
        "write": "file_write",
        "dosya_yaz": "file_write",
        
        # Terminal komut çalıştırma işlemleri
        "terminal_execute": "terminal_execute",
        "terminal_run": "terminal_execute",
        "command_run": "terminal_execute",
        "run_command": "terminal_execute",
        "exec": "terminal_execute",
        "komut_çalıştır": "terminal_execute",
        
        # Tarayıcı işlemleri
        "browser_search": "browser_search",
        "tarayıcıda_ara": "browser_search",
        "search_on_site": "browser_search",
        "site_arama": "browser_search",
        
        "browser_shop_online": "browser_shop_online",
        "online_alışveriş": "browser_shop_online",
        
        "add_to_cart": "browser_universal_add_to_cart",
        "sepete_ekle": "browser_universal_add_to_cart",
        
        "browser_comprehensive_search": "browser_comprehensive_search",
        "kapsamlı_arama": "browser_comprehensive_search"
    }
    
    # Eylem adını varsa mapping'ten al, yoksa orijinal adı kullan
    action_type = action_type_mapping.get(action_type, action_type)
    
    # Path parametrelerindeki kullanıcı adını değiştir
    if 'path' in params:
        user_name = os.environ.get("USER", "")
        params['path'] = params['path'].replace("<kullanıcı_adı>", user_name)
        params['path'] = params['path'].replace("<username>", user_name)
        params['path'] = params['path'].replace("<user>", user_name)
        params['path'] = params['path'].replace("~", os.path.expanduser("~"))
    
    # LLM'in sık kullandığı bilgi eylemleri için destek ekle
    if action_type == "system_info" or action_type == "system_message":
        info_type = params.get("info_type", "")
        message = params.get("message", "")
        
        # Kullanılabilecek sistem bilgilerini döndür
        system_info = {
            "introduction": "Ben AI Helper, macOS bilgisayarınızda yerel olarak çalışan bir yapay zeka asistanıyım. "
                          "Dosyaları okuyabilir, yazabilir, uygulamaları açabilir ve tarayıcı üzerinde işlemler yapabilirim.",
            "capabilities": "Yapabileceklerimin bazıları: Dosya ve klasör işlemleri, tarayıcıda arama yapma, "
                          "uygulama açma/kapatma, terminal komutları çalıştırma ve ekran görüntüsü alma.",
            "system": f"İşletim Sistemi: {platform.system()} {platform.release()}\n"
                    f"Python Sürümü: {platform.python_version()}\n"
                    f"Bilgisayar Adı: {platform.node()}"
        }
        
        # Mesaj parametresi tercih edilir
        if message:
            response_message = message
        else:
            # Bilgi türüne göre yanıt oluştur
            response_message = system_info.get(info_type, system_info["introduction"])
        
        return {
            "success": True,
            "action": action_type,
            "message": response_message
        }
    
    # Yeni eklenen kod - Çoklu eylemleri işle
    if action_type == "multiple_actions":
        results = []
        sub_actions = params.get("actions", [])
        
        for action in sub_actions:
            sub_action_type = action.get("action", "")
            sub_params = action.get("params", {})
            
            result = execute_action(sub_action_type, sub_params, 
                                  browser_controller, app_controller, 
                                  file_controller, screen_controller)
            results.append(result)
        
        # Tüm alt işlemlerin başarılı olup olmadığını kontrol et
        all_successful = all(r.get("success", False) for r in results)
        return {
            "success": all_successful,
            "action": action_type,
            "message": "Tüm eylemler başarıyla tamamlandı" if all_successful else "Bazı eylemler başarısız oldu",
            "results": results
        }
    
    # Browser actions
    elif action_type.startswith("browser_"):
        return browser_controller.execute_browser_action(action_type, params)
    
    # App actions
    elif action_type.startswith("app_"):
        return app_controller.execute_app_action(action_type, params)
    
    # File actions
    elif action_type.startswith("file_"):
        return file_controller.execute_file_action(action_type, params)
    
    # Klasör oluşturma eylemi
    elif action_type == "folder_create":
        path = params.get("path", "")
        folder_name = params.get("folder_name", "")
        
        # Kullanıcı adını otomatik olarak al
        path = path.replace("<kullanıcı_adı>", os.environ.get("USER", ""))
        
        # Eğer folder_name belirtilmemişse ve path tam bir dosya yolu ise, bunu ayır
        if not folder_name and "/" in path:
            # En son / işaretinden sonrasını folder_name olarak al
            parts = path.rsplit("/", 1)
            if len(parts) == 2:
                path, folder_name = parts[0], parts[1]
        
        # Folder_name hala yoksa, varsayılan değer kullan
        if not folder_name:
            folder_name = "yeni_klasor"
        
        full_path = os.path.join(path, folder_name)
        
        try:
            os.makedirs(full_path, exist_ok=True)
            return {
                "success": True,
                "action": action_type,
                "message": f"Klasör oluşturuldu: {full_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "action": action_type,
                "message": f"Klasör oluşturma hatası: {str(e)}"
            }
    
    # Dosya oluşturma eylemi
    elif action_type == "file_create":
        path = params.get("path", "")
        file_name = params.get("file_name", "")
        file_content = params.get("file_content", "")
        file_extension = params.get("extension", "")  # Yeni parametre: uzantı
        
        # Eski parametrelere geriye dönük uyumluluk için destek
        if not file_content and "content" in params:
            file_content = params.get("content", "")
        
        # İçerik yoksa varsayılan değer ata
        if not file_content:
            file_extension_lower = file_extension.lower() if file_extension else ""
            
            # Uzantıya göre varsayılan içerik belirle
            if ".txt" in path.lower() or file_extension_lower in [".txt", "txt"]:
                file_content = "Bu bir metin dosyasıdır."
            elif ".py" in path.lower() or file_extension_lower in [".py", "py"]:
                file_content = "# Bu bir Python dosyasıdır\nprint('Merhaba, Dünya!')"
            elif ".html" in path.lower() or file_extension_lower in [".html", "html"]:
                file_content = "<!DOCTYPE html>\n<html>\n<head>\n  <title>Yeni HTML Sayfası</title>\n</head>\n<body>\n  <h1>Merhaba, Dünya!</h1>\n</body>\n</html>"
            elif ".js" in path.lower() or file_extension_lower in [".js", "js"]:
                file_content = "// Bu bir JavaScript dosyasıdır\nconsole.log('Merhaba, Dünya!');"
            elif ".css" in path.lower() or file_extension_lower in [".css", "css"]:
                file_content = "/* Bu bir CSS dosyasıdır */\nbody {\n  font-family: Arial, sans-serif;\n}"
            else:
                file_content = "Bu bir dosyadır."
        
        print(f"DEBUG - Başlangıç parametreleri: path={path}, file_name={file_name}, extension={file_extension}")
        
        # Kullanıcı adını otomatik olarak al - birden fazla formatı destekle
        user_name = os.environ.get("USER", "")
        path = path.replace("<kullanıcı_adı>", user_name)
        path = path.replace("<username>", user_name)
        path = path.replace("<user>", user_name)
        path = path.replace("~", os.path.expanduser("~"))
        
        # Path değerini parçala
        if "/" in path and file_name == "":
            # Yolun son kısmı dosya adı olabilir - uzantıya bak
            _, ext = os.path.splitext(path)
            if ext:  # Eğer uzantı varsa (.py, .txt, vb.)
                # Bu bir dosya yolu, kök dizini ve dosya adını ayır
                folder_path = os.path.dirname(path)
                file_name = os.path.basename(path)
                path = folder_path
            else:
                # Bu bir klasör yolu olabilir - varsayılan dosya adı kullan
                file_name = "yeni_dosya"  # Uzantısız varsayılan isim
        
        # Kesin dosya adı belirle
        if not file_name:
            file_name = "yeni_dosya"  # Uzantısız varsayılan isim
        
        # Dosya adında uzantı kontrolü ve uzantı ekleme
        name, ext = os.path.splitext(file_name)
        
        # Eğer dosya adında bir uzantı yoksa ve belirtilen bir uzantı varsa ekle
        if not ext:
            if file_extension:
                # Uzantı başında nokta yoksa ekle
                if not file_extension.startswith('.'):
                    file_extension = '.' + file_extension
                file_name = name + file_extension
                print(f"DEBUG - Dosya adına belirtilen uzantı eklendi: {file_name}")
        
        # Tam dosya yolu oluştur - clean path
        if path.endswith('/'):
            path = path[:-1]
        
        # Dosya yolunu birleştir
        full_path = os.path.join(path, file_name)
        
        print(f"DEBUG - İşlenmiş parametreler: klasör={path}, dosya={file_name}")
        print(f"DEBUG - Tam dosya yolu: {full_path}")
        
        try:
            # Klasörü oluştur
            folder_path = os.path.dirname(full_path)
            os.makedirs(folder_path, exist_ok=True)
            print(f"DEBUG - Klasör oluşturuldu/kontrol edildi: {folder_path}")
            
            # Dosyayı oluştur
            with open(full_path, "w") as f:
                f.write(file_content)
            
            print(f"DEBUG - Dosya başarıyla oluşturuldu: {full_path}")
            return {
                "success": True,
                "action": action_type,
                "message": f"Dosya başarıyla oluşturuldu: {full_path}"
            }
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"DEBUG - Dosya oluşturma hatası: {str(e)}\nTraceback: {error_details}")
            return {
                "success": False, 
                "action": action_type,
                "message": f"Dosya oluşturma hatası: {str(e)}"
            }
    
    # Screen actions
    elif action_type.startswith("screen_"):
        return screen_controller.execute_screen_action(action_type, params)
    
    # Dosya yazma eylemi
    elif action_type == "file_write":
        path = params.get("path", "")
        content = params.get("content", "")
        
        # Kullanıcı adını otomatik olarak al
        user_name = os.environ.get("USER", "")
        path = path.replace("<kullanıcı_adı>", user_name)
        path = path.replace("<username>", user_name)
        path = path.replace("<user>", user_name)
        path = path.replace("~", os.path.expanduser("~"))
        
        print(f"DEBUG - Dosya yazma: {path}, içerik uzunluğu: {len(content)}")
        
        try:
            # Klasörü oluştur (yoksa)
            folder_path = os.path.dirname(path)
            if folder_path and not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)
                print(f"DEBUG - Klasör oluşturuldu: {folder_path}")
            
            # Dosyaya yaz
            with open(path, "w") as f:
                f.write(content)
            
            print(f"DEBUG - Dosyaya yazıldı: {path}")
            return {
                "success": True,
                "action": action_type,
                "message": f"Dosyaya başarıyla yazıldı: {path}"
            }
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"DEBUG - Dosya yazma hatası: {str(e)}\n{error_details}")
            return {
                "success": False,
                "action": action_type,
                "message": f"Dosya yazma hatası: {str(e)}"
            }
    
    # Unknown action type
    elif action_type == "terminal_execute" or action_type == "command_run":
        # Terminal komutu çalıştırma işlevi
        command = params.get("command", "")
        commands = params.get("commands", [])
        
        # Tek bir komut veya komut listesi kontrolü
        if not command and not commands:
            return {
                "success": False,
                "action": action_type,
                "message": "Komut belirtilmedi"
            }
        
        # Kullanıcı adını değiştir ve komutları çalıştır
        user_name = os.environ.get("USER", "")
        results = []
        
        # Tek komut durumu
        if command:
            command = command.replace("<kullanıcı_adı>", user_name)
            command = command.replace("<username>", user_name)
            command = command.replace("<user>", user_name)
            command = command.replace("~", os.path.expanduser("~"))
            
            print(f"DEBUG - Terminal komutu çalıştırılıyor: {command}")
            
            try:
                import subprocess
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"DEBUG - Komut başarıyla çalıştırıldı: {command}")
                    return {
                        "success": True,
                        "action": action_type,
                        "message": f"Komut başarıyla çalıştırıldı: {command}",
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }
                else:
                    print(f"DEBUG - Komut çalıştırma hatası: {command} - {result.stderr}")
                    return {
                        "success": False,
                        "action": action_type,
                        "message": f"Komut çalıştırma hatası: {result.stderr}",
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }
            except Exception as e:
                print(f"DEBUG - Komut çalıştırma hatası: {str(e)}")
                return {
                    "success": False,
                    "action": action_type,
                    "message": f"Komut çalıştırma hatası: {str(e)}"
                }
        
        # Komut listesi durumu
        elif commands:
            all_successful = True
            all_stdout = []
            all_stderr = []
            
            for cmd in commands:
                cmd = cmd.replace("<kullanıcı_adı>", user_name)
                cmd = cmd.replace("<username>", user_name)
                cmd = cmd.replace("<user>", user_name)
                cmd = cmd.replace("~", os.path.expanduser("~"))
                
                print(f"DEBUG - Terminal komutu çalıştırılıyor: {cmd}")
                
                # Özel komut işleme - echo ile Python kodu yazma kontrolü
                if cmd.startswith("echo") and ".py" in cmd and ">" in cmd:
                    try:
                        # echo komutunu dosya yazma işlemine dönüştür
                        parts = cmd.split(">", 1)
                        if len(parts) == 2:
                            # İçerik ve dosya yolunu çıkar
                            content_part = parts[0].strip()[5:]  # "echo " kısmını çıkar
                            file_path = parts[1].strip()
                            
                            # İçeriği tek veya çift tırnaklardan temizle
                            if (content_part.startswith("'") and content_part.endswith("'")) or \
                               (content_part.startswith('"') and content_part.endswith('"')):
                                content = content_part[1:-1]
                            else:
                                content = content_part
                            
                            # Dosyayı doğrudan Python kullanarak yaz
                            folder_path = os.path.dirname(file_path)
                            if folder_path and not os.path.exists(folder_path):
                                os.makedirs(folder_path, exist_ok=True)
                                
                            with open(file_path, "w") as f:
                                f.write(content)
                                
                            print(f"DEBUG - Dosyaya içerik yazıldı: {file_path}")
                            all_stdout.append(f"Dosya başarıyla oluşturuldu: {file_path}")
                            continue
                    except Exception as e:
                        print(f"DEBUG - Özel komut işleme hatası: {str(e)}")
                        all_successful = False
                        all_stderr.append(f"Dosya yazma hatası: {str(e)}")
                        continue
                
                # Normal komut çalıştırma
                try:
                    import subprocess
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print(f"DEBUG - Komut başarıyla çalıştırıldı: {cmd}")
                        all_stdout.append(result.stdout)
                        all_stderr.append(result.stderr)
                    else:
                        print(f"DEBUG - Komut çalıştırma hatası: {cmd} - {result.stderr}")
                        all_successful = False
                        all_stdout.append(result.stdout)
                        all_stderr.append(result.stderr)
                except Exception as e:
                    print(f"DEBUG - Komut çalıştırma hatası: {str(e)}")
                    all_successful = False
                    all_stderr.append(str(e))
            
            # Tüm komutlar için sonuç döndür
            return {
                "success": all_successful,
                "action": action_type,
                "message": "Tüm komutlar başarıyla çalıştırıldı" if all_successful else "Bazı komutlar çalıştırılamadı",
                "stdout": "\n".join(all_stdout),
                "stderr": "\n".join(all_stderr)
            }
    # Unknown action type
    else:
        return {
            "success": False,
            "action": action_type,
            "message": f"Bilinmeyen eylem türü: {action_type}"
        }

if __name__ == "__main__":
    main()
