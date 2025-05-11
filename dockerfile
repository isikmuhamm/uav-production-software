# d:\WebProjects\uav-production-software\Dockerfile

# Temel Python imajını kullan (projen Python 3.12+ kullandığı için)
FROM python:3.12-slim

# Ortam değişkenleri
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Çalışma dizinini ayarla
WORKDIR /app

# PostgreSQL client'ı yükle (entrypoint.sh içinde pg_isready için gerekli)
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# requirements.txt dosyasını kopyala ve bağımlılıkları yükle
# Önce requirements.txt'yi kopyalayıp yüklemek, katman önbelleğinden faydalanmayı sağlar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını kopyala
COPY . .

# entrypoint.sh script'ini kopyala ve çalıştırılabilir yap
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Django uygulamasının çalışacağı portu aç
EXPOSE 8000

# Konteyner başladığında çalışacak komut
ENTRYPOINT ["/app/entrypoint.sh"]
