<?php
// Fichier de diagnostic TEMPORAIRE (01/09/2026) — chronomètre chaque étape
// du démarrage Symfony à la main (autoload, .env, construction du Kernel,
// boot, traitement d'une Request) pour savoir PRÉCISÉMENT où passent les
// 12-18 secondes observées sur /api/tennis_matches/1, alors que PHP+MySQL
// bruts (voir _diag_db.php) répondent en quelques millisecondes.
use App\Kernel;
use Symfony\Component\Dotenv\Dotenv;
use Symfony\Component\HttpFoundation\Request;

header('Content-Type: application/json');
$timings = [];
$t0 = microtime(true);

require dirname(__DIR__).'/vendor/autoload.php';
$timings['require_autoload_ms'] = round((microtime(true) - $t0) * 1000, 2);

$t0b = microtime(true);
(new Dotenv())->bootEnv(dirname(__DIR__).'/.env');
$timings['dotenv_boot_ms'] = round((microtime(true) - $t0b) * 1000, 2);

$t1 = microtime(true);
$kernel = new Kernel($_SERVER['APP_ENV'] ?? 'dev', (bool) ($_SERVER['APP_DEBUG'] ?? true));
$timings['new_kernel_ms'] = round((microtime(true) - $t1) * 1000, 2);

$t2 = microtime(true);
$kernel->boot();
$timings['kernel_boot_ms'] = round((microtime(true) - $t2) * 1000, 2);

$t3 = microtime(true);
$container = $kernel->getContainer();
$timings['get_container_ms'] = round((microtime(true) - $t3) * 1000, 2);

$t4 = microtime(true);
$request = Request::create('/api/tennis_matches/1', 'GET', [], [], [], [], null);
$request->headers->set('Accept', 'application/ld+json');
$response = $kernel->handle($request);
$timings['kernel_handle_ms'] = round((microtime(true) - $t4) * 1000, 2);
$timings['response_status'] = $response->getStatusCode();
$timings['response_len'] = strlen($response->getContent());

$timings['total_ms'] = round((microtime(true) - $t0) * 1000, 2);

$kernel->terminate($request, $response);

echo json_encode($timings, JSON_PRETTY_PRINT);
