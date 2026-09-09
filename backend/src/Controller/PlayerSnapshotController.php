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
 * GET /api/players/{id}/snapshot — "forme du moment" d'un joueur : service,
 * retour, dynamique récente (Elo sur les 8 derniers matchs), repos, minutes
 * jouées sur les 10 derniers jours, taux d'exploit contre plus fort classé,
 * efficacité face aux gauchers/droitiers (voir player_snapshot, migration
 * Version20260908150000, et ml-service/import_upcoming_matches.py qui la
 * rafraîchit chaque nuit).
 *
 * Cette table alimente déjà EN INTERNE le radar comparatif et le modèle de
 * prédiction (PlayerComparisonService, PredictionService) — les axes
 * "Service", "Retour", "Forme" et "Repos" du radar en sont des versions
 * normalisées 1-99 — mais les vrais chiffres n'étaient jusqu'ici affichés
 * nulle part, ni sur la fiche match ni sur le comparateur.
 *
 * Même règle d'accès que PlayerCareerStatsController/PlayerHeadToHeadController
 * (voir ces classes) : réservé à l'admin ou à un abonné actif.
 */
#[Route('/api/players/{id}/snapshot', name: 'player_snapshot', methods: ['GET'])]
#[IsGranted(
    new Expression("is_granted('ROLE_ADMIN') or (is_granted('ROLE_USER') and user.hasActiveSubscription())"),
    message: "Forme du moment réservée aux abonnés et à l'admin.",
)]
final class PlayerSnapshotController extends AbstractController
{
    public function __construct(
        private readonly Connection $connection,
    ) {
    }

    public function __invoke(int $id): JsonResponse
    {
        $row = $this->connection->fetchAssociative(
            'SELECT serve_score, return_score, momentum, recent_form, days_rest, fatigue_minutes, '
            . 'upset_rate, winrate_vs_left, winrate_vs_right, updated_at FROM player_snapshot WHERE player_id = ?',
            [$id]
        );

        if ($row === false) {
            return $this->json(
                ['detail' => "Pas de données de forme récente disponibles pour ce joueur."],
                Response::HTTP_NOT_FOUND,
            );
        }

        return $this->json($row);
    }
}
