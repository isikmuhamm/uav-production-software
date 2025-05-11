#!/bin/sh

# Hata durumunda script'i sonlandır
set -e

# docker-compose.yml'den gelen ortam değişkenlerini kullan
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-django_project_user}
DB_NAME=${DB_NAME:-hava_araci_uretim_db}
# DB_PASSWORD, PGPASSWORD olarak ayarlanacak

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."

# pg_isready'nin şifre sormaması için PGPASSWORD ortam değişkenini ayarla
export PGPASSWORD="$DB_PASSWORD"

# PostgreSQL hazır olana kadar bekle
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -q; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "PostgreSQL is up - executing commands"

echo "Applying database migrations..."
python manage.py migrate --noinput

# Statik dosyaları toplamak istersen (DEBUG=False ise genellikle gerekir):
# echo "Collecting static files..."
# python manage.py collectstatic --noinput --clear

echo "Starting Django development server..."
# 0.0.0.0 tüm arayüzlerden erişime izin verir
exec python manage.py runserver 0.0.0.0:8000