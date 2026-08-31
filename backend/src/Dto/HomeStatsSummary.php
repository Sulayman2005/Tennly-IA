<?php

namespace App\Dto;

use ApiPlatform\Metadata\ApiResource;
use ApiPlatform\Metadata\Get;
use App\State\HomeStatsProvider;

/**
 * Ressource en lecture seule pour GET /api/stats — les chiffres mis en avant
 * sur la page d'accueil (bandeau du haut + bandeau animé de HomeView.vue).
 * Volontairement accessible sans authentification, comme
 * ModelReliabilitySummary : c'est la toute première chose qu'un visiteur
 * non-abonné voit sur le site.
 *
 * Remplace les valeurs fixes qui étaient codées en dur dans HomeView.vue
 * (voir son ancien commentaire TODO) — suit le même principe "aucune donnée
 * inventée" que ModelReliabilitySummary/AdminDashboardSummary : chaque champ
 * vient d'une vraie requête sur les données en base, et vaut `null` quand
 * l'échantillon est insuffisant plutôt qu'une valeur neutre inventée. C'est
 * au frontend de l'afficher comme "pas encore assez de données", jamais au
 * backend de fabriquer un chiffre.
 *
 * Cas particulier à connaître : `averageValueEdgePercent` vaut aujourd'hui
 * TOUJOURS `null`, quel que soit le nombre d'analyses en base —
 * Prediction::$valueEdge n'est encore jamais renseigné par ml-service
 * (aucune source de cotes de marché n'est encore intégrée, voir le
 * commentaire sur Prediction::$marketOddsFavorite). Le jour où ce signal
 * existera réellement, ce endpoint le calculera automatiquement, sans
 * changement de code ici — voir HomeStatsProvider::computeAverageValueEdgePercent().
 */
#[ApiResource(
    operations: [
        new Get(
            uriTemplate: '/stats',
            provider: HomeStatsProvider::class,
        ),
    ],
)]
final class HomeStatsSummary
{
    public function __construct(
        public readonly ?float $successRateLast90Days,
        public readonly int $analyzedMatchesCount,
        public readonly ?float $averageValueEdgePercent,
        public readonly ?float $brierScore,
        public readonly ?float $yearsOfHistory,
    ) {
    }
}
