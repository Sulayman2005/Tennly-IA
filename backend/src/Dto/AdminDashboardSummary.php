<?php

namespace App\Dto;

use ApiPlatform\Metadata\ApiResource;
use ApiPlatform\Metadata\Get;
use App\State\AdminDashboardProvider;

/**
 * Ressource en lecture seule pour GET /api/admin/dashboard (back-office,
 * cahier des charges section 3.7, écran "Tableau de bord" de admin.html).
 *
 * N'est adossée à aucune entité Doctrine : AdminDashboardProvider calcule
 * chaque champ à partir de vraies requêtes sur les tables existantes
 * (subscription, plan, tennis_match, prediction). Suit le même principe que
 * le service ML (voir README "Aucune donnée n'est inventée") : quand un
 * agrégat n'est pas encore calculable (aucun match terminé, par exemple),
 * le champ correspondant vaut `null` plutôt qu'une valeur neutre inventée.
 * Volontairement absent d'ici : tout ce qui nécessiterait une donnée qui
 * n'existe pas encore côté produit (supervision réelle du pipeline
 * d'ingestion, calendrier des tournois à venir — voir README "reste à
 * faire") plutôt que d'afficher un widget avec un contenu fictif.
 */
#[ApiResource(
    operations: [
        new Get(
            uriTemplate: '/admin/dashboard',
            security: "is_granted('ROLE_ADMIN')",
            provider: AdminDashboardProvider::class,
        ),
    ],
)]
final class AdminDashboardSummary
{
    /**
     * @param list<array{code: string, name: string, count: int}> $subscribersByPlan
     * @param list<array{surface: string, accuracy: float, sampleSize: int}> $modelAccuracyBySurface
     * @param list<array{date: string, count: int}> $subscriptionsGrowth Un point par jour, 14 derniers jours
     *        (y compris aujourd'hui), triés du plus ancien au plus récent — jours sans nouvel abonnement
     *        inclus avec count=0, jamais omis (pour un tracé continu côté frontend).
     */
    public function __construct(
        public readonly int $activeSubscriptionsCount,
        public readonly array $subscribersByPlan,
        public readonly int $mrrCents,
        public readonly ?float $modelAccuracyOverall,
        public readonly array $modelAccuracyBySurface,
        public readonly int $predictionsCount,
        public readonly int $finishedMatchesWithPredictionCount,
        public readonly int $upcomingMatchesCount,
        public readonly int $totalUsersCount,
        public readonly int $newUsersLast7Days,
        public readonly int $canceledSubscriptionsLast30Days,
        public readonly array $subscriptionsGrowth,
    ) {
    }
}
