<?php
// Fichier de diagnostic TEMPORAIRE (01/09/2026) — à supprimer une fois le
// souci de lenteur généralisée de l'API résolu et confirmé. Ne passe pas par
// Symfony (fichier réel dans public/, servi directement par Apache) : sert
// uniquement à vérifier, depuis le navigateur, si OPcache est bien chargé et
// actif après le rebuild de l'image Docker, sans avoir besoin d'un terminal.
header('Content-Type: application/json');

$status = function_exists('opcache_get_status') ? opcache_get_status(false) : null;

// Petit benchmark local : recharge un fichier vendor/ existant plusieurs
// fois pour donner un ordre de grandeur du coût de compilation/lecture
// fichier sur ce système, indépendamment de toute requête SQL.
$vendorFile = __DIR__ . '/../vendor/autoload.php';
$t0 = microtime(true);
for ($i = 0; $i < 20; $i++) {
    // require_once ne recharge qu'une fois réellement, mais file_exists()/
    // stat() sont refaits à chaque itération, ce qui est justement ce qu'on
    // veut mesurer (coût des accès fichier sur le bind mount).
    file_exists($vendorFile);
    clearstatcache(true, $vendorFile);
}
$statLoopMs = round((microtime(true) - $t0) * 1000, 2);

echo json_encode([
    'php_version' => PHP_VERSION,
    'opcache_extension_loaded' => extension_loaded('Zend OPcache'),
    'opcache_enabled' => $status['opcache_enabled'] ?? null,
    'opcache_memory_usage' => $status['memory_usage'] ?? null,
    'opcache_stats' => $status['opcache_statistics'] ?? null,
    'stat_loop_20x_ms_on_bind_mount' => $statLoopMs,
], JSON_PRETTY_PRINT);
