#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tarayıcı Ajanı Çalıştırma Betiği

Bu betik, tarayıcı ajanının "Düşün-Araştır-Gözlemle-Eyleme Geç" döngüsünü
kullanarak web üzerinde akıllı araştırmalar yapmasını sağlar.

Yerel LLM modellerini (Ollama veya Local AI) kullanarak çalışır,
herhangi bir API anahtarı gerektirmez.
"""

import os
import sys
import argparse
import subprocess
import requests
from planner_executor import BrowserAgent

def check_ollama_running():
    """Ollama'nın çalışıp çalışmadığını kontrol et."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_ollama_if_needed():
    """Ollama çalışmıyorsa başlat."""
    if not check_ollama_running():
        print("Ollama çalışmıyor. Başlatılıyor...")
        try:
            # Arkaplanda Ollama'yı başlat
            subprocess.Popen(["ollama", "serve"], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            
            # Başlamasını bekle
            import time
            for _ in range(5):  # 5 saniye bekle
                time.sleep(1)
                if check_ollama_running():
                    print("Ollama başlatıldı!")
                    return True
            
            print("Ollama başlatılamadı. Manuel olarak 'ollama serve' komutunu çalıştırın.")
            return False
        except Exception as e:
            print(f"Ollama başlatılırken hata: {e}")
            print("Ollama yüklü olmayabilir. Kurulum için: https://ollama.com/download")
            return False
    return True

def list_available_models():
    """Kullanılabilir yerel modelleri listele."""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = [model["name"] for model in response.json().get("models", [])]
            return models
        return []
    except:
        return []

def main():
    """Ana program fonksiyonu."""
    parser = argparse.ArgumentParser(description="Tarayıcı Ajanını çalıştır (Yerel LLM ile)")
    parser.add_argument("--query", "-q", type=str, help="Araştırılacak sorgu")
    parser.add_argument("--model", "-m", type=str, default="llama2", 
                      help="Kullanılacak yerel model adı (varsayılan: llama2)")
    parser.add_argument("--steps", "-s", type=int, default=8, 
                      help="Maksimum adım sayısı (varsayılan: 8)")
    parser.add_argument("--verbose", "-v", action="store_true",
                      help="Detaylı çıktı göster")
    parser.add_argument("--list-models", "-l", action="store_true",
                      help="Kullanılabilir modelleri listele ve çık")
    
    args = parser.parse_args()
    
    # Ollama'nın çalıştığından emin ol
    if not start_ollama_if_needed():
        return 1
    
    # Modelleri listele ve çık
    if args.list_models:
        models = list_available_models()
        if models:
            print("Kullanılabilir modeller:")
            for model in models:
                print(f"  - {model}")
        else:
            print("Hiç model bulunamadı. 'ollama pull llama2' komutu ile model indirebilirsiniz.")
        return 0
    
    # Sorguyu komut satırından veya kullanıcı girdisinden al
    query = args.query
    if not query:
        query = input("Soru veya araştırma konusunu yazın: ")
    
    # Ajanı başlat
    agent = BrowserAgent(model=args.model)
    agent.max_steps = args.steps
    
    print(f"\n🔍 Araştırılıyor: {query}")
    print(f"🤖 Model: {args.model}")
    print("⏳ Bu işlem biraz zaman alabilir...\n")
    
    # Ajanı çalıştır ve sonucu al
    if args.verbose:
        print("🔄 Adımlar başlatılıyor...\n")
    
    result = agent.run(query)
    
    # Sonucu göster
    print("\n📊 Araştırma Sonucu:")
    print("-" * 50)
    print(result)
    print("-" * 50)
    
    # Eğer detaylı mod aktifse, adım kayıtlarını göster
    if args.verbose and agent.scratchpad:
        print("\n🔍 Araştırma Adımları:")
        for i, item in enumerate(agent.scratchpad):
            if item["role"] == "assistant" and "THOUGHT:" in item["content"]:
                thought = item["content"].split("THOUGHT:")[1].split("ACTION:")[0].strip() if "THOUGHT:" in item["content"] else ""
                action = item["content"].split("ACTION:")[1].strip() if "ACTION:" in item["content"] else ""
                print(f"\nAdım {i//2 + 1}:")
                if thought:
                    print(f"  Düşünce: {thought[:100]}...")
                if action:
                    print(f"  Eylem: {action}")
    
    # Her adımdan sonra şunu ekleyelim:
    if len(agent.scratchpad) > 2:
        agent.scratchpad.append({"role": "system", "content": "Devam et, sonuca ulaşmadın! Daha fazla araştır ve bilgileri analiz et."})
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 