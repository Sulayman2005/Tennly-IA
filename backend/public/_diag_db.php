<?php
// Fichier de diagnostic TEMPORAIRE (01/09/2026) — isole le coût d'une
// connexion PDO + requêtes triviales vers MySQL, indépendamment de Doctrine/
// Symfony/OPcache, pour savoir si la lenteur vient du réseau Docker vers le
// conteneur "db" plutôt que du PHP applicatif.
header('Content-Type: application/json');

$dsn = 'mysql:host=db;port=3306;dbname=tennly;charset=utf8mb4';
$out = [];

$t0 = microtime(true);
try {
    $pdo = new PDO($dsn, 'root', 'root_dev_only', [PDO::ATTR_TIMEOUT => 10]);
    $out['connect_ms'] = round((microtime(true) - $t0) * 1000, 2);
} catch (\Throwable $e) {
    $out['connect_error'] = $e->getMessage();
    $out['connect_ms'] = round((microtime(true) - $t0) * 1000, 2);
    echo json_encode($out, JSON_PRETTY_PRINT);
    exit;
}

// 5 SELECT 1 successifs, pour voir le coût PAR requête une fois connecté.
$out['select_1_runs_ms'] = [];
for ($i = 0; $i < 5; $i++) {
    $t1 = microtime(true);
    $pdo->query('SELECT 1')->fetchAll();
    $out['select_1_runs_ms'][] = round((microtime(true) - $t1) * 1000, 2);
}

// Une vraie requête représentative : un match avec ses jointures (playerA,
// playerB, prediction, favoritePlayer) à la main, en UNE SEULE requête SQL
// (pas via Doctrine/hydratation) pour isoler le temps MySQL pur.
$t2 = microtime(true);
$pdo->query('
    SELECT m.id, pa.full_name AS player_a, pb.full_name AS player_b,
           pr.probability_favorite, pf.full_name AS favorite
    FROM tennis_match m
    JOIN player pa ON pa.id = m.player_a_id
    JOIN player pb ON pb.id = m.player_b_id
    LEFT JOIN prediction pr ON pr.match_id = m.id
    LEFT JOIN player pf ON pf.id = pr.favorite_player_id
    WHERE m.id = 1
')->fetchAll();
$out['joined_match_query_ms'] = round((microtime(true) - $t2) * 1000, 2);

// Même chose mais pour 50 lignes (simule la collection /api/tennis_matches).
$t3 = microtime(true);
$pdo->query('
    SELECT m.id, pa.full_name AS player_a, pb.full_name AS player_b,
           pr.probability_favorite, pf.full_name AS favorite
    FROM tennis_match m
    JOIN player pa ON pa.id = m.player_a_id
    JOIN player pb ON pb.id = m.player_b_id
    LEFT JOIN prediction pr ON pr.match_id = m.id
    LEFT JOIN player pf ON pf.id = pr.favorite_player_id
    LIMIT 50
')->fetchAll();
$out['joined_50_matches_query_ms'] = round((microtime(true) - $t3) * 1000, 2);

echo json_encode($out, JSON_PRETTY_PRINT);
