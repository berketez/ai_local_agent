"""
LLM Inference - Handles inference and action extraction from LLM responses

This module provides functionality to process user input through the LLM
and extract actionable commands from the responses.
"""

import json
import re
from typing import List, Dict, Any

class LLMInference:
    """Handles LLM inference and action extraction."""
    
    def __init__(self, llm_model):
        """
        Initialize the inference engine.
        
        Args:
            llm_model: The loaded LLM model
        """
        self.llm = llm_model
        self.system_prompt = """
        Sen kullanıcının macOS bilgisayarında yerel olarak çalışan bir AI asistansın.
        Adın AI Helper. Kullanıcının bilgisayarını doğrudan kontrol edebilirsin.
        
        Kullanıcı senden bilgisayarda bir eylem yapmanı istediğinde, şöyle yanıt ver:
        1. Ne yapacağını açıklayan kısa ve yararlı bir mesaj
        2. Eylemi tanımlayan bir JSON eylem bloğu
        
        JSON formatını şöyle kullan (backtick içinde):
        ```json
        {"action": "eylem_adı", "params": {"parametre1": "değer1", "parametre2": "değer2"}}
        ```
        
        Eylem komut örnekleri:
        {"action": "browser_open", "params": {"url": "https://example.com"}}
        {"action": "file_read", "params": {"path": "/path/to/file.txt"}}
        {"action": "app_open", "params": {"app_name": "Safari"}}
        
        ÖNEMLİ:
        1. Tüm eylemler için tam izinlerin var. Kullanıcıdan ayrıca izin isteme.
        2. Eylem komutlarını tam ve doğru biçimde kullandığından emin ol.
        3. JSON formatı kesinlikle doğru olmalı - hatalı JSON eylemlerinin çalışmayacağını unutma.
        4. Her zaman geçerli 'action' ve 'params' anahtarlarını kullan.
        5. Sistem istekleri doğrudan yerine getirilecektir.
        """
        self.conversation_history = []
        # Hata düzeltme ipuçları
        self.error_correction_prompt = """
        Daha önce verdiğim yanıtta JSON formatı ile ilgili bir sorun olabilir. Lütfen şu kurallara dikkat ederek tekrar deneyeceğim:
        
        1. Eylem JSON'ları mutlaka şu formatta olmalı:
           {"action": "eylem_adı", "params": {"parametre1": "değer1"}}
        
        2. JSON formatı kesinlikle doğru olmalı:
           - Tüm anahtarlar çift tırnak içinde olmalı (")
           - String değerler çift tırnak içinde olmalı
           - Boşluklar ve girintiler doğru olmalı
        
        3. Desteklenen eylem tipleri:
           - browser_open, browser_search
           - file_read, file_write, file_create, file_delete
           - app_open, app_close
           - terminal_execute, command_run
           - folder_create
        
        Düzeltilmiş yanıtım:
        """
    
    def process_input(self, user_input: str) -> str:
        """
        Process user input through the LLM.
        
        Args:
            user_input: The user's input text
            
        Returns:
            The LLM's response
        """
        # Hata düzeltme promptu olup olmadığını kontrol et
        is_error_correction = False
        if user_input.strip().startswith("Önceki yanıtınızı işlerken bir hata oluştu:"):
            is_error_correction = True
            # Mevcut sistem promptuna hata düzeltme ipuçlarını ekle
            temp_system_prompt = self.system_prompt + "\n\n" + """
            ÖNEMLİ HATA DÜZELTME NOTU:
            Önceki yanıtınızda bir hata vardı. Lütfen JSON formatını düzeltin.
            JSON'da çift tırnak kullanın, geçerli parametre adları kullanın.
            Her JSON bloğu için action ve params anahtarlarını doğru şekilde kullanın.
            JSON'u başka bir formatta değil, tam olarak şu formatta verin:
            {"action": "eylem_adı", "params": {"parametre1": "değer1"}}
            
            Yanıtınıza şu şekilde başlayın:
            "Bir hata oluştu, tekrar deniyorum. "
            """
        else:
            temp_system_prompt = self.system_prompt
        
        # Add user input to conversation history
        if not is_error_correction:
            self.conversation_history.append({"role": "user", "content": user_input})
        
        # Prepare the prompt with system instructions and conversation history
        prompt = self._prepare_prompt(temp_system_prompt)
        
        # Generate response from LLM
        response = self.llm(
            prompt,
            max_tokens=2048,
            stop=["User:"],
            echo=False
        )
        
        # Extract the generated text
        generated_text = response.get("choices", [{}])[0].get("text", "")
        
        # Add response to conversation history (only if not error correction)
        if not is_error_correction:
            self.conversation_history.append({"role": "assistant", "content": generated_text})
        else:
            # Hata düzeltme yanıtı ise son yanıtı güncelle ve kullanıcıya hata düzeltme mesajı göster
            if self.conversation_history and self.conversation_history[-1]["role"] == "assistant":
                # Eğer yanıt zaten "Bir hata oluştu" ile başlamıyorsa, bu metni ekle
                if not generated_text.strip().startswith("Bir hata oluştu"):
                    generated_text = "Bir hata oluştu, tekrar deniyorum. " + generated_text
                
                # Son yanıtı güncelle
                self.conversation_history[-1]["content"] = generated_text
        
        return generated_text
    
    def _prepare_prompt(self, system_prompt: str) -> str:
        """
        Prepare the prompt with system instructions and conversation history.
        
        Args:
            system_prompt: System prompt to use
            
        Returns:
            The formatted prompt string
        """
        prompt = f"System: {system_prompt}\n\n"
        
        # Add conversation history
        for message in self.conversation_history:
            role = message["role"].capitalize()
            content = message["content"]
            prompt += f"{role}: {content}\n\n"
        
        prompt += "Assistant: "
        return prompt
    
    def extract_actions(self, response: str) -> List[Dict[str, Any]]:
        """
        Extract action requests from the LLM response.
        
        Args:
            response: The LLM's response text
            
        Returns:
            List of action dictionaries
        """
        actions = []
        
        # JSON kod bloğunu bul (```json ... ``` veya backtick içinde)
        json_code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', response)
        
        # Kod bloklarından JSON'ları çıkar
        for block in json_code_blocks:
            try:
                # Temizleme işlemleri
                cleaned_block = block.strip()
                
                # Çoklu JSON nesneleri olabilir, her satırı dene
                for line in cleaned_block.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('//') or line.startswith('#'):
                        continue
                    
                    try:
                        # Satırı JSON olarak ayrıştırmayı dene
                        action_data = json.loads(line)
                        if "action" in action_data:
                            actions.append({
                                "type": action_data["action"],
                                "params": action_data.get("params", {})
                            })
                    except json.JSONDecodeError:
                        pass
                
                # Tüm bloğu tek JSON olarak ayrıştırmayı dene
                if not actions:
                    action_data = json.loads(cleaned_block)
                    if "action" in action_data:
                        actions.append({
                            "type": action_data["action"],
                            "params": action_data.get("params", {})
                        })
            except json.JSONDecodeError:
                pass
        
        # Kod bloğu dışındaki JSON'ları çıkar
        if not actions:
            # Çok satırlı JSON'larla başa çıkmak için gelişmiş yaklaşım
            try:
                # Tüm olası JSON bloklarını bul (açılış-kapanış parantezlerini sayarak)
                i = 0
                while i < len(response):
                    # JSON başlangıcını bul
                    start_pos = response.find('{', i)
                    if start_pos == -1:
                        break
                        
                    # Açılış-kapanış parantezlerini dengele
                    open_braces = 1
                    j = start_pos + 1
                    
                    while j < len(response) and open_braces > 0:
                        if response[j] == '{':
                            open_braces += 1
                        elif response[j] == '}':
                            open_braces -= 1
                        j += 1
                        
                    # Eğer parantezler dengeliyse, JSON blok bulundu
                    if open_braces == 0:
                        json_block = response[start_pos:j]
                        
                        try:
                            # Format düzeltme - yeni satırları temizle
                            cleaned_json = json_block.replace('\n', ' ').replace('\r', '')
                            action_data = json.loads(cleaned_json)
                            
                            if "action" in action_data:
                                actions.append({
                                    "type": action_data["action"],
                                    "params": action_data.get("params", {})
                                })
                                print(f"Eylem çıkarıldı: {action_data['action']}")
                        except json.JSONDecodeError as e:
                            # Gelişmiş temizleme dene
                            try:
                                # Yeni satırları ve fazla boşlukları temizle
                                cleaned_json = ' '.join(json_block.split())
                                # Tırnak işaretlerini kontrol et ve düzelt
                                cleaned_json = re.sub(r'([{,])\s*(\w+):', r'\1"\2":', cleaned_json)
                                cleaned_json = cleaned_json.replace("'", '"')
                                action_data = json.loads(cleaned_json)
                                
                                if "action" in action_data:
                                    actions.append({
                                        "type": action_data["action"],
                                        "params": action_data.get("params", {})
                                    })
                            except Exception:
                                print(f"JSON çözümlenemedi: {json_block}")
                        
                    i = j if j > i else i + 1
                        
            except Exception as e:
                print(f"Eylem çıkarma hatası: {str(e)}")
        
        return actions
    
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
