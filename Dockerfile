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
#
# NOTE (29/08/2026, v2) : composer.json déclare "php": ">=8.2", mais le
# composer.lock réel (généré par le WAMP local, qui tourne visiblement en PHP
# 8.3+) verrouille des versions de paquets qui exigent PHP >= 8.3 — le
# platform_check.php généré par Composer le confirme à l'exécution. PHP 8.2
# donnait donc une Fatal error au premier chargement. On passe l'image en PHP
# 8.3 pour matcher le composer.lock existant plutôt que de toucher au lock.
FROM php:8.3-apache

# --- Extensions PHP ---------------------------------------------------
# pdo_mysql : nécessaire pour Doctrine (MySQL/MariaDB) — ctype et iconv
# (requis par composer.json) sont déjà activés par défaut dans l'image PHP
# officielle, rien à installer pour elles.
RUN docker-php-ext-install pdo_mysql

# --- OPcache : activé même en dev (01/09/2026) ---------------------------
# L'image php:apache officielle inclut l'extension opcache mais la laisse
# ÉTEINTE par défaut : sans elle, PHP reparse et recompile TOUT le code
# (Symfony + Doctrine + vendor/, plusieurs milliers de fichiers) à CHAQUE
# requête, depuis zéro. Combiné au bind mount Windows de ./backend (voir
# docker-compose.yml) — notoirement lent pour les accès fichier par fichier
# sous Docker Desktop (WSL2/Hyper-V) — ça suffit à expliquer, à soi seul,
# des requêtes de plusieurs secondes même sur un simple GET par id (constaté :
# 12s sur GET /api/tennis_matches/{id}, sans aucun rapport avec le nombre de
# requêtes SQL). validate_timestamps=1 (pas 0, le réglage "prod") garde le
# rechargement à chaud : une modif enregistrée dans VS Code reste prise en
# compte à la requête suivante, sans rebuild ni redémarrage du conteneur —
# seul le temps de RECOMPILATION répétée à chaque requête disparaît.
# realpath_cache_size/_ttl : même logique pour les résolutions de chemin
# (autoload Composer, require Symfony) sur ce même bind mount lent.
#
# (01/09/2026, v2) Premier essai insuffisant : écrire seulement les réglages
# opcache.* ci-dessous NE SUFFIT PAS à activer l'extension — le module
# opcache.so de l'image officielle est présent mais jamais CHARGÉ tant
# qu'aucune ligne "zend_extension=opcache" n'existe dans un fichier ini.
# Sans ça, PHP ignore silencieusement des directives pour un module non
# chargé (aucune erreur), ce qui explique qu'aucun gain n'ait été mesuré
# après le premier rebuild (18s, identique à avant). `docker-php-ext-enable`
# (fourni par l'image officielle) écrit cette ligne pour nous, avec le bon
# chemin vers le .so pour ce build précis.
RUN docker-php-ext-enable opcache

RUN { \
        echo 'opcache.enable=1'; \
        echo 'opcache.validate_timestamps=1'; \
        echo 'opcache.revalidate_freq=0'; \
        echo 'opcache.memory_consumption=256'; \
        echo 'opcache.interned_strings_buffer=16'; \
        echo 'opcache.max_accelerated_files=20000'; \
        echo 'realpath_cache_size=4096K'; \
        echo 'realpath_cache_ttl=600'; \
    } > /usr/local/etc/php/conf.d/opcache-dev.ini

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