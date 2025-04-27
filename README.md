 AI Helper

AI Helper, macOS sisteminizle doğal dil komutları aracılığıyla etkileşime girmenizi sağlayan, yerel olarak çalışan bir LLM (Large Language Model) destekli yapay zeka asistanıdır.

## Özellikleri

- **Yerel LLM Entegrasyonu**: Ollama veya LM Studio aracılığıyla yerel LLM modellerini kullanma
- **Sistem Etkileşimi**: Dosya işlemleri, web tarayıcı kontrolü, uygulama yönetimi ve ekran kontrolü
- **İzin Sistemi**: Sistem işlemlerinden önce kullanıcı izni isteme
- **Terminal Arayüzü**: Kullanıcı dostu terminal tabanlı arayüz

## Gereksinimler

- Python 3.8 veya daha yeni
- macOS işletim sistemi
- Aşağıdaki Python paketleri:
  - llama-cpp-python
  - pyautogui
  - pillow
  - pytesseract
  - rich

## Kurulum

Bağımlılıkları yüklemek için:

```bash
pip install -r requirements.txt
```

Veya kurulum betiğini çalıştırın:

```bash
./install.sh
```

## Kullanım

AI Helper'ı terminal üzerinden başlatmak için:

```bash
# Otomatik backend tespiti ile
python src/main.py --backend auto --model <model_adı>

# Belirli bir backend seçimi ile
python src/main.py --backend ollama --model llama3.2
python src/main.py --backend lmstudio_sdk --model llama-3.2-1b-instruct
```

### Komut Satırı Seçenekleri

- `--backend`: Kullanılacak LLM backend'i (`auto`, `ollama`, `lmstudio_sdk`, `lmstudio_openai`) - Varsayılan: `auto`
- `--model`: Kullanılacak model adı (zorunlu)
- `--context-length`: Model için bağlam uzunluğu (varsayılan: 4096)
- `--temperature`: Metin üretimi için sıcaklık değeri (varsayılan: 0.7)
- `--verbose` veya `-v`: Ayrıntılı çıktıyı etkinleştirme

## Etkileşim Örnekleri

AI Helper çalıştığında, doğal dil kullanarak etkileşimde bulunabilirsiniz:

### Web Tarama
```
> Safari'yi aç ve apple.com'a git
> Google'da "en son macOS özellikleri" için arama yap
```

### Dosya İşlemleri
```
> Masaüstünde todo.txt adında yeni bir metin dosyası oluştur
> ~/Documents/notes.txt dosyasının içeriğini oku
> İndirmeler klasörümdeki tüm dosyaları listele
```

### Uygulama Kontrolü
```
> Hesap Makinesi uygulamasını aç
> Safari'yi kapat
> Çalışan tüm uygulamaları listele
```

### Sistem Etkileşimi
```
> Ekranımın ekran görüntüsünü al
> Mevcut uygulamada "Merhaba dünya!" yaz
> Faremi ekranın ortasına taşı ve tıkla
```

## Mimari

AI Helper şu ana bileşenlerden oluşur:

1. **LLM Entegrasyonu**: Yerel modelleri yükler ve kullanır
2. **İzin Sistemi**: Sistem eylemleri öncesinde kullanıcı izni ister
3. **Sistem Etkileşim Katmanı**: Sistem işlemlerini gerçekleştirir
4. **Komut Yorumlayıcı**: Doğal dil komutlarını yorumlar
5. **Terminal Arayüzü**: Kullanıcı etkileşimini yönetir

## Güvenlik

- Tüm izinler açıkça istenir ve iptal edilebilir
- Veriler harici sunuculara gönderilmez (tamamen yerel çalışır)
- Gerçekleştirilen tüm eylemlerin açık kaydı tutulur
- Mümkün olduğunca korumalı çalıştırma

## İzin Yönetimi

AI Helper, sisteminizle etkileşimde bulunan işlemlerden önce her zaman izin ister. Şunları yapabilirsiniz:

- Tek bir eylem için izin ver
- Bir eylem kategorisi için izin ver
- Belirli bir süre sonra sona eren geçici izin ver

## Çıkış

AI Helper'dan çıkmak için şunlardan birini yazın:
```
exit
```
veya
```
quit
```

## Lisans

Bu proje lisansı için LICENSE dosyasına bakınız.
