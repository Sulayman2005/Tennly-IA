<?php

namespace App\Dto;

use ApiPlatform\Metadata\ApiResource;
use ApiPlatform\Metadata\Get;
use App\State\ModelReliabilityProvider;

/**
 * Ressource en lecture seule pour GET /api/model-reliability — page publique
 * "Fiabilité du modèle". Volontairement accessible sans authentification
 * (contrairement à Prediction, réservée aux abonnés) : le but est justement
 * de convaincre un visiteur non-abonné, avec des chiffres vérifiables plutôt
 * qu'une promesse marketing.
 *
 * Suit le même principe que AdminDashboardSummary (voir README "Aucune
 * donnée n'est inventée") : chaque chiffre vient d'une vraie comparaison
 * Prediction::favoritePlayer vs TennisMatch::winner sur des matchs
 * réellement terminés. Quand l'échantillon est nul pour un point donné,
 * le champ vaut `null` plutôt qu'une valeur neutre inventée.
 */
#[ApiResource(
    operations: [
        new Get(
            uriTemplate: '/model-reliability',
            provider: ModelReliabilityProvider::class,
        ),
    ],
)]
final class ModelReliabilitySummary
{
    /**
     * @param list<array{surface: string, accuracy: float, sampleSize: int}> $accuracyBySurface
     * @param list<array{rangeLabel: string, rangeMin: float, rangeMax: float, predictedAvg: ?float, actualWinRate: ?float, sampleSize: int}> $calibrationBuckets
     */
    public function __construct(
        public readonly int $finishedMatchesWithPredictionCount,
        public readonly ?float $overallAccuracy,
        public readonly array $accuracyBySurface,
        public readonly array $calibrationBuckets,
        public readonly ?string $modelVersion,
    ) {
    }
}