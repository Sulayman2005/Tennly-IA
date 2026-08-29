# Image unique PHP (Apache) + Python, pour remplacer WAMP en local.
#
# NOTE (29/08/2026) : PlayerComparisonService::predict() appelle
# ml-service/predict_pair.py en sous-processus, via un chemin RELATIF
# ($this->projectDir . '/../ml-service/predict_pair.py' — voir ce fichier).
# Pour ne rien changer à ce code, on garde donc PHP et Python dans le MÊME
# conteneur, avec exactement la même disposition de dossiers qu'en local :
#   /var/www/html/backend      (Symfony, projectDir)
#   /var/www/html/ml-service   (scripts Python, sibling de backend/)
# Le frontend Vue (Vite) n'est PAS dans ce conteneur : WAMP ne servait que le
# back (Apache+MySQL+PHP), le frontend tournait déjà nativement via
# `npm run dev` en dehors de WAMP — ça continue de fonctionner à l'identique,
# voir DOCKER.md.
FROM php:8.2-apache

# --- Extensions PHP ---------------------------------------------------
# pdo_mysql : nécessaire pour Doctrine (MySQL/MariaDB) — ctype et iconv
# (requis par composer.json) sont déjà activés par défaut dans l'image PHP
# officielle, rien à installer pour elles.
RUN docker-php-ext-install pdo_mysql

# --- Composer -----------------------------------------------------------
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# --- Python (pour ml-service) + unzip -------------------------------------
# python3-pip suffit ; --break-system-packages est nécessaire sur les images
# Debian récentes (PEP 668, "externally-managed-environment") — même
# convention que celle déjà utilisée pour pip dans ce projet.
# unzip : l'image php:apache officielle ne l'inclut pas par défaut, et
# Composer en a besoin pour extraire les paquets téléchargés (sans lui,
# `composer install` échoue avec une erreur sur l'extension zip manquante).
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        unzip \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY ml-service/requirements.txt /tmp/ml-service-requirements.txt
RUN pip3 install --break-system-packages --no-cache-dir -r /tmp/ml-service-requirements.txt

# --- Apache : DocumentRoot -> backend/public -----------------------------
# Astuce standard pour les images php:apache dont le code applicatif vit
# dans un sous-dossier (ici backend/public, le front controller Symfony)
# plutôt qu'à la racine /var/www/html.
RUN sed -ri -e 's!/var/www/html!/var/www/html/backend/public!g' \
        /etc/apache2/sites-available/*.conf \
        /etc/apache2/apache2.conf \
        /etc/apache2/conf-available/*.conf \
    && a2enmod rewrite

# public/.htaccess (fourni par le squelette Symfony) a besoin de
# AllowOverride All pour que la réécriture d'URL vers index.php fonctionne.
RUN { \
        echo '<Directory /var/www/html/backend/public>'; \
        echo '    AllowOverride All'; \
        echo '    Require all granted'; \
        echo '</Directory>'; \
    } > /etc/apache2/conf-available/z-symfony.conf \
    && a2enconf z-symfony

WORKDIR /var/www/html

EXPOSE 80
