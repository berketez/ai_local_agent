import os
import json
import time
import subprocess
import requests
from typing import List, Dict, Any, Optional
from browser import BrowserController

class LocalModelClient:
    """Yerel LLM modellerini çalıştırmak için istemci.
    Ollama veya LocalAI gibi hizmetlerle çalışır."""
    
    def __init__(self, model_name="llama2", server_url="http://localhost:11434"):
        """Yerel model istemcisini başlat.
        
        Args:
            model_name: Kullanılacak model adı (örn. llama2, mistral, gemma)
            server_url: Model sunucusunun URL'si
        """
        self.model_name = model_name
        self.server_url = server_url
        self.check_model_availability()
    
    def check_model_availability(self):
        """Yerel modelin kullanılabilir olup olmadığını kontrol et."""
        try:
            # Ollama kullanımı için
            response = requests.get(f"{self.server_url}/api/tags")
            available_models = [model["name"] for model in response.json().get("models", [])]
            
            if self.model_name not in available_models:
                print(f"UYARI: {self.model_name} modeli yüklü değil. Otomatik olarak indiriliyor...")
                subprocess.run(["ollama", "pull", self.model_name], check=True)
        except Exception as e:
            print(f"Yerel model kontrolü başarısız: {e}")
            print("Ollama çalışmıyor olabilir. 'ollama serve' komutu ile başlatın.")
    
    def chat_completion(self, messages, tools=None):
        """Chat completion API'sine benzer bir arayüz sağlar."""
        try:
            # Ollama chat formatına dönüştür
            prompt = self._convert_messages_to_prompt(messages, tools)
            
            # Ollama API'si ile istek gönder
            response = requests.post(
                f"{self.server_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            response_json = response.json()
            response_text = response_json.get("response", "")
            
            # Araç çağrısı var mı kontrol et
            tool_calls = self._extract_tool_calls(response_text, tools)
            
            # ChatCompletion benzeri bir yapı döndür
            return SimpleResponse(response_text, tool_calls)
        except Exception as e:
            print(f"Yerel model çağrısı başarısız: {e}")
            return SimpleResponse("Yerel model yanıt veremedi. Hata: " + str(e), [])
    
    def _convert_messages_to_prompt(self, messages, tools=None):
        """Mesajları tek bir prompt metni olarak birleştir."""
        prompt = ""
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                prompt += f"<s>[SYSTEM]\n{content}\n</s>\n\n"
            elif role == "user":
                prompt += f"<s>[USER]\n{content}\n</s>\n\n"
            elif role == "assistant":
                prompt += f"<s>[ASSISTANT]\n{content}\n</s>\n\n"
            else:
                prompt += f"<s>[{role.upper()}]\n{content}\n</s>\n\n"
        
        # Araçlar hakkında bilgi ekle
        if tools:
            prompt += "<s>[SYSTEM]\nAşağıdaki araçları kullanabilirsin:\n"
            for tool in tools:
                prompt += f"- {tool['name']}: {tool['description']}\n"
            prompt += "Bir araç kullanmak için şu formatta yanıt ver:\nACTION: { \"name\":\"ARAÇ_ADI\", \"arguments\":{ \"parametre\":\"değer\" } }\n</s>\n\n"
            
        prompt += "<s>[ASSISTANT]\n"
        return prompt
    
    def _extract_tool_calls(self, text, tools):
        """Metin içerisinden araç çağrılarını çıkar."""
        if not tools or "ACTION:" not in text:
            return []
        
        try:
            # ACTION: bölümünü bul
            action_parts = text.split("ACTION:")
            if len(action_parts) < 2:
                return []
            
            # JSON kısmını çıkar ve parse et
            action_json_text = action_parts[1].strip()
            
            # JSON başlangıç ve bitiş indekslerini bul
            json_start = action_json_text.find("{")
            json_end = action_json_text.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = action_json_text[json_start:json_end]
                action_data = json.loads(json_str)
                
                tool_name = action_data.get("name")
                arguments = action_data.get("arguments", {})
                
                return [SimpleToolCall(tool_name, arguments)]
        except Exception as e:
            print(f"Araç çağrısı çıkarma hatası: {e}")
        
        return []

class SimpleResponse:
    """OpenAI yanıtına benzer basit bir yanıt sınıfı."""
    
    def __init__(self, content, tool_calls):
        self.choices = [SimpleChoice(content, tool_calls)]

class SimpleChoice:
    """Basit bir seçim nesnesi."""
    
    def __init__(self, content, tool_calls):
        self.message = SimpleMessage(content, tool_calls)
        self.finish_reason = "tool_calls" if tool_calls else "stop"

class SimpleMessage:
    """Basit bir mesaj nesnesi."""
    
    def __init__(self, content, tool_calls):
        self.content = content
        self.tool_calls = tool_calls

class SimpleToolCall:
    """Basit bir araç çağrısı nesnesi."""
    
    def __init__(self, function_name, arguments):
        self.function = SimpleFunction(function_name, arguments)

class SimpleFunction:
    """Basit bir fonksiyon nesnesi."""
    
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = json.dumps(arguments)

class BrowserAgent:
    """Düşün-Araştır-Gözlemle-Eyleme Geç döngüsünü kullanarak tarayıcı üzerinde 
    akıllı işlemler yapabilen bir ajan."""
    
    def __init__(self, model="llama2"):
        """Browser Controller ile birlikte çalışan ajanı başlat."""
        self.browser = BrowserController()
        self.model_name = model
        self.llm = LocalModelClient(model_name=model)
        self.scratchpad = []
        self.max_steps = 8
        
        # Ajan için araç tanımları
        self.tools = [
            {
                "name": "NAV",
                "description": "Herhangi bir URL'ye git",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"]
                }
            },
            {
                "name": "SEARCH",
                "description": "Bir arama motoru veya belirli bir sitede sorgu çalıştır",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "engine": {"type": "string", "enum": ["google", "bing"]},
                        "site": {"type": "string"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "CLICK",
                "description": "Metni belirtilen desene uyan n. görünür bağlantıya tıkla",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "index": {"type": "integer", "default": 0}
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "EXTRACT_JS",
                "description": "Mevcut sayfanın JS analizini ve HTML özetini döndür",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "BACK",
                "description": "Tarayıcıda bir önceki sayfaya dön",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
        
        # Sistem prompt şablonu
        self.system_prompt = """# Rol: Kıdemli araştırmacı ajansın planlayıcısısın.
## Aşama etiketleri
- THOUGHT: İç muhakemen
- ACTION: tools listesinden _sadece bir_ komut
- OBSERVATION: Executor tarafından eklenecek, SEN YAZMA
- FINAL: Kullanıcıya nihai cevabın (bu bölümden sonra döngü bitecek)

Görev: "{user_request}"

Diğer talimatlar:
- En fazla {max_steps} ACTION dene.
- Eğer OBSERVATION içinde "No relevant results" görürsen farklı query üret.
- Aynı domain içinde 2'den fazla click yapma.
- Emin olamadığında devam etmeden önce daha fazla bilgi topla.
- Türkçe sorulara sonunda Türkçe cevap ver.

Başla.
"""
    
    def run_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Planner'dan gelen aracı BrowserController'a ilet ve sonuçları al."""
        result = {}
        
        try:
            if name == "NAV":
                browser_result = self.browser.execute_browser_action("browser_open", {
                    "url": args.get("url", "")
                })
                
                # Sayfanın HTML özeti ve başlığını da ekle
                html_summary = self.browser.extract_javascript()
                observation = {
                    "success": browser_result.get("success", False),
                    "current_url": self.browser.current_url,
                    "page_title": html_summary.get("title", ""),
                    "page_summary": self._get_page_summary(html_summary)
                }
                
            elif name == "SEARCH":
                params = {
                    "query": args.get("query", ""),
                    "engine": args.get("engine", None),
                    "site": args.get("site", None)
                }
                browser_result = self.browser.execute_browser_action("browser_search", params)
                
                # Sonuç sayfasını incele
                self.browser._examine_search_results(args.get("query", ""), 5)
                
                # Sayfanın HTML özeti ve başlığını ekle
                html_summary = self.browser.extract_javascript()
                observation = {
                    "success": browser_result.get("success", False),
                    "current_url": self.browser.current_url,
                    "page_title": html_summary.get("title", ""),
                    "search_results": self._get_search_results(html_summary)
                }
                
            elif name == "CLICK":
                # DOM tabanlı tıklama - JavaScript ile daha güvenilir
                script = f'''
                (function() {{
                    const pattern = "{args.get('pattern', '')}";
                    const index = {args.get('index', 0)};
                    const links = Array.from(document.querySelectorAll('a')).filter(
                        a => a.textContent && a.textContent.toLowerCase().includes(pattern.toLowerCase())
                    );
                    
                    if (links.length > index) {{
                        links[index].scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        setTimeout(() => {{ links[index].click(); }}, 500);
                        return true;
                    }}
                    return false;
                }})();
                '''
                
                # Tarayıcı eylemini çalıştır
                browser_result = self.browser.execute_browser_action("browser_next_result", {})
                time.sleep(2)  # Biraz bekleyelim
                
                # Yeni URL'yi ve sayfa içeriğini kontrol et
                self.browser._refresh_current_url()
                html_summary = self.browser.extract_javascript()
                
                observation = {
                    "success": browser_result.get("success", False),
                    "current_url": self.browser.current_url,
                    "page_title": html_summary.get("title", ""),
                    "page_content": self._get_page_summary(html_summary)
                }
                
            elif name == "EXTRACT_JS":
                # Sayfanın JavaScript analizini ve HTML özetini al
                js_analysis = self.browser.extract_javascript()
                
                observation = {
                    "success": True,
                    "current_url": self.browser.current_url,
                    "page_title": js_analysis.get("title", ""),
                    "page_summary": self._get_page_summary(js_analysis),
                    "forms": js_analysis.get("forms", []),
                    "navigation_links": [
                        {"text": link.get("text", ""), "href": link.get("href", "")} 
                        for link in js_analysis.get("navigations", [])[:10]  # Sadece ilk 10 link
                    ]
                }
                
            elif name == "BACK":
                # Tarayıcıda geri git
                script = f'''
                window.history.back();
                '''
                
                # Geri düğmesine tıklamayı simüle et
                browser_result = True
                time.sleep(1)
                
                # Yeni URL'yi ve sayfa içeriğini kontrol et
                self.browser._refresh_current_url()
                html_summary = self.browser.extract_javascript()
                
                observation = {
                    "success": True,
                    "current_url": self.browser.current_url,
                    "page_title": html_summary.get("title", ""),
                    "page_content": self._get_page_summary(html_summary)
                }
            
            else:
                observation = {
                    "error": f"Bilinmeyen araç: {name}",
                    "success": False
                }
                
            # BrowserController tarafından URL güncellemesi yap
            self.browser._refresh_current_url()
            
            return observation
            
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }
    
    def _get_page_summary(self, js_analysis: Dict[str, Any]) -> str:
        """Sayfa içeriğinin özetini almak için yardımcı bir metot."""
        # Sayfanın title ve URL'sini al
        page_title = js_analysis.get("title", "")
        page_url = js_analysis.get("url", "")
        
        # Sayfadaki önemli metinleri topla
        texts = []
        
        # Form bilgilerini ekle
        forms = js_analysis.get("forms", [])
        if forms:
            texts.append(f"FORMS: {len(forms)} form bulundu.")
            for i, form in enumerate(forms[:2]):  # Sadece ilk 2 form
                form_id = form.get("id", f"Form-{i}")
                form_action = form.get("action", "")
                texts.append(f"Form[{form_id}] action={form_action}")
        
        # Navigasyon bağlantılarını ekle
        links = js_analysis.get("navigations", [])
        if links:
            texts.append(f"LINKS: {len(links)} bağlantı bulundu. İlk 10 tanesi:")
            for i, link in enumerate(links[:10]):  # Sadece ilk 10 bağlantı
                link_text = link.get("text", "").strip()
                link_href = link.get("href", "")
                if link_text and len(link_text) > 0:
                    texts.append(f"Link[{i}]: '{link_text}' -> {link_href}")
        
        # Sayfa metni ve önemli içeriği buraya ekle
        # Örneğin ana başlıklar, paragraflar vs.
        
        # Özeti bir araya getir
        summary = f"PAGE TITLE: {page_title}\nURL: {page_url}\n\n"
        summary += "\n".join(texts)
        
        return summary
    
    def _get_search_results(self, js_analysis: Dict[str, Any]) -> str:
        """Arama sonuçlarının özetini almak için yardımcı metot."""
        # Navigasyon bağlantılarını arama sonucu olarak kullan
        links = js_analysis.get("navigations", [])
        results = []
        
        if links:
            results.append(f"{len(links)} arama sonucu bulundu. İlk 10 tanesi:")
            for i, link in enumerate(links[:10]):  # Sadece ilk 10 bağlantı
                link_text = link.get("text", "").strip()
                link_href = link.get("href", "")
                if link_text and len(link_text) > 0:
                    results.append(f"Result[{i}]: '{link_text}' -> {link_href}")
                    
        if not results:
            return "Arama sonucu bulunamadı."
            
        return "\n".join(results)
    
    def run(self, user_request: str) -> str:
        """Ajan mantığını çalıştır ve sonucu al."""
        step = 0
        self.scratchpad = []
        
        # Kullanıcı isteğini sistem yönergesine ekle
        messages = [{"role": "system", "content": self.system_prompt.format(
            user_request=user_request,
            max_steps=self.max_steps
        )}]
        
        while step < self.max_steps:
            # Yerel LLM'e istek gönder
            response = self.llm.chat_completion(messages, self.tools)
            
            # Yanıtı al
            message = response.choices[0].message
            message_text = message.content or ""
            
            # Yanıtı işle
            if "FINAL:" in message_text:
                # Son yanıtı al
                final_answer = message_text.split("FINAL:")[1].strip()
                # Kullanıcı yanıtını güncelle ve döndür
                return final_answer
                
            # Araç kullanımı varsa işle
            if hasattr(message, 'tool_calls') and message.tool_calls:
                call = message.tool_calls[0]
                tool_name = call.function.name
                args = json.loads(call.function.arguments)
                
                # Yanıtı ve aracı scratchpad'e ekle
                self.scratchpad.append({"role": "assistant", "content": message_text})
                messages.append({"role": "assistant", "content": message_text})
                
                # Aracı çalıştır ve gözlemi al
                observation = self.run_tool(tool_name, args)
                observation_text = json.dumps(observation, ensure_ascii=False, indent=2)
                
                # Gözlemi scratchpad'e ekle
                observation_message = f"OBSERVATION: {observation_text}"
                self.scratchpad.append({"role": "user", "content": observation_message})
                messages.append({"role": "user", "content": observation_message})
                
                # Log olarak da yaz
                print(f"Adım {step+1}: {tool_name}")
                print(f"Parametreler: {args}")
                print(f"Gözlem: {observation_text[:100]}...")
                
            else:
                # Araç kullanımı yoksa, normal yanıtı scratchpad'e ekle
                self.scratchpad.append({"role": "assistant", "content": message_text})
                messages.append({"role": "assistant", "content": message_text})
            
            step += 1
        
        # Maksimum adım sayısına ulaşıldı
        return "Maksimum adım sayısına ulaşıldı, sonuç bulunamadı."

# Uygulamayı çalıştırmak için örnek kod
if __name__ == "__main__":
    agent = BrowserAgent()
    
    # Örnek sorgu
    result = agent.run("iPhone 15 özellikleri neler ve en ucuz fiyatı nedir?")
    print("\nAraştırma Sonucu:")
    print(result) 