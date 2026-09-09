<?php

namespace App\Controller;

use Doctrine\DBAL\Connection;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\ExpressionLanguage\Expression;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Security\Http\Attribute\IsGranted;

/**
 * GET /api/players/{id}/career-stats — palmarès carrière complet d'un
 * joueur (victoires/défaites par surface, statistiques de service, période
 * couverte) — LiveTennisAPI, palier Basic (voir
 * ml-service/import_career_stats_livetennisapi.py et la migration
 * Version20260909120000 pour le schéma de player_career_stats).
 *
 * Même règle d'accès que ComparateurController/Prediction (voir ces
 * classes) : réservé à l'admin ou à un abonné actif — donnée "premium",
 * cohérente avec le reste de l'analyse détaillée du site.
 */
#[Route('/api/players/{id}/career-stats', name: 'player_career_stats', methods: ['GET'])]
#[IsGranted(
    new Expression("is_granted('ROLE_ADMIN') or (is_granted('ROLE_USER') and user.hasActiveSubscription())"),
    message: 'Statistiques de carrière réservées aux abonnés et à l\'admin.',
)]
final class PlayerCareerStatsController extends AbstractController
{
    public function __construct(
        private readonly Connection $connection,
    ) {
    }

    public function __invoke(int $id): JsonResponse
    {
        $row = $this->connection->fetchAssociative(
            'SELECT wins, losses, titles, wins_hard, losses_hard, wins_clay, losses_clay, '
            . 'wins_grass, losses_grass, wins_carpet, losses_carpet, aces, aces_per_match, '
            . 'double_faults, first_in_pct, first_won_pct, second_won_pct, bp_saved_pct, '
            . 'span_first, span_last, updated_at FROM player_career_stats WHERE player_id = ?',
            [$id]
        );

        if ($row === false) {
            return $this->json(
                ['detail' => 'Pas de statistiques de carrière disponibles pour ce joueur.'],
                Response::HTTP_NOT_FOUND,
            );
        }

        return $this->json($row);
    }
}
