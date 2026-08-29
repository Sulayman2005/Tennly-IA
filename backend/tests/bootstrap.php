<?php

use Symfony\Component\Dotenv\Dotenv;

require dirname(__DIR__).'/vendor/autoload.php';

// Charge .env / .env.local si présents — inoffensif pour les tests unitaires
// actuels (qui ne lisent aucune variable d'environnement), mais nécessaire
// dès qu'un test futur touchera au kernel Symfony ou à Doctrine.
if (method_exists(Dotenv::class, 'bootEnv') && file_exists(dirname(__DIR__).'/.env')) {
    (new Dotenv())->bootEnv(dirname(__DIR__).'/.env');
}