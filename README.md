# Tarayıcı Ajanı - Düşün-Araştır-Gözlemle-Eyleme Geç Döngüsü

Bu proje, bir tarayıcı ajanının "Düşün-Araştır-Gözlemle-Eyleme Geç" döngüsünü kullanarak web üzerinde akıllı araştırmalar yapmasını sağlar. Ajan, yerel LLM (Large Language Model) modellerini kullanarak çalışır ve herhangi bir API anahtarı gerektirmez.

## Özellikler

- ✅ Planner-Executor mimari yapısı ile karmaşık görevleri bağımsız tamamlama
- ✅ Yerel LLM modelleriyle (Ollama) tamamen açık kaynak çalışma
- ✅ Tam otomatik web araştırması ve bilgi çıkarımı
- ✅ Kendi kendine düşünme, tarayıcıda gezinme ve bilgi değerlendirme
- ✅ Sonuçları anlaşılır bir özet olarak raporlama

## Kurulum

### Gereksinimler

- Python 3.8+
- [Ollama](https://ollama.com/download) (Yerel LLM modelleri için)

### Adımlar

1. Bu repoyu klonlayın:

```bash
git clone https://github.com/kullaniciadi/tarayici-ajani.git
cd tarayici-ajani
```

2. Gerekli Python paketlerini yükleyin:

```bash
pip install requests
```

3. Ollama'yı yükleyin ve başlatın:

```bash
# macOS veya Linux
curl -fsSL https://ollama.com/install.sh | sh
ollama serve

# Windows
# https://ollama.com/download adresinden indirip yükleyin
```

4. Modelleri indirin:

```bash
ollama pull llama2    # veya başka bir model
```

## Kullanım

Ajanı çalıştırmak için:

```bash
python run_agent.py --query "iPhone 15 özellikleri neler ve en ucuz fiyatı nedir?"
```

### Komut Satırı Parametreleri

- `--query`, `-q`: Araştırılacak sorgu
- `--model`, `-m`: Kullanılacak yerel model adı (varsayılan: llama2)
- `--steps`, `-s`: Maksimum adım sayısı (varsayılan: 8)
- `--verbose`, `-v`: Detaylı çıktı göster
- `--list-models`, `-l`: Kullanılabilir modelleri listele ve çık

### Örnek

```bash
python run_agent.py --query "Yapay zeka nedir ve günlük hayatta nasıl kullanılır?" --model mistral --verbose
```

## Çalışma Prensibi

Ajan, "Düşün-Araştır-Gözlemle-Eyleme Geç" döngüsünü şu şekilde uygular:

1. **Düşünme Aşaması**: LLM, görevi anlar ve bir aksiyon planı oluşturur
2. **Araştırma**: Uygun arama motorlarında veya belirli sitelerde arama yapar
3. **Gözlemleme**: Arama sonuçlarını inceler ve ne yapacağına karar verir
4. **Eyleme Geçme**: Linklere tıklama, sayfalarda gezinme, bilgi çıkarma işlemlerini yapar
5. **Değerlendirme**: Toplanan bilgileri değerlendirir ve kapsamlı bir yanıt oluşturur

## Mimari

Sistem iki ana bileşenden oluşur:

1. **Planner (LLM)**: Yapılacak işlemlere karar verir
2. **Executor (Browser Controller)**: Planner'ın kararlarını tarayıcı üzerinde uygular

Bu ayrım, ajanın her adımda düşünme ve gözlem döngüsü yaparak ilerlemesini sağlar.

## Destek

Eğer sorularınız veya önerileriniz varsa, lütfen GitHub Issues üzerinden iletişime geçin.

## Lisans

Bu proje MIT Lisansı altında lisanslanmıştır.
