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
 * GET /api/players/{id}/head-to-head/{opponentId} — bilan des confrontations
 * directes entre deux joueurs suivis, calculé sur TOUT l'historique ATP/WTA
 * connu (pas seulement les quelques matchs affichés dans /matchs) — voir
 * player_head_to_head (migration Version20260908150000) et
 * ml-service/import_upcoming_matches.py, qui rafraîchit cette table chaque
 * nuit. Cette même table alimente déjà l'axe "H2H" du radar comparatif
 * (PlayerComparisonService::fetchHeadToHead), mais seulement sous forme d'un
 * score normalisé 1-99 — cet endpoint expose le VRAI décompte de victoires,
 * jusque-là présent en base mais jamais affiché nulle part sur le site.
 *
 * La table stocke une seule ligne par paire, indexée par (player_low_id,
 * player_high_id) triés par id croissant — cet endpoint réordonne la
 * réponse du point de vue de {id} pour que le frontend n'ait jamais à
 * connaître cette convention de stockage.
 *
 * Même règle d'accès que PlayerCareerStatsController/ComparateurController
 * (voir ces classes) : réservé à l'admin ou à un abonné actif.
 */
#[Route('/api/players/{id}/head-to-head/{opponentId}', name: 'player_head_to_head', methods: ['GET'])]
#[IsGranted(
    new Expression("is_granted('ROLE_ADMIN') or (is_granted('ROLE_USER') and user.hasActiveSubscription())"),
    message: "Face-à-face réservé aux abonnés et à l'admin.",
)]
final class PlayerHeadToHeadController extends AbstractController
{
    public function __construct(
        private readonly Connection $connection,
    ) {
    }

    public function __invoke(int $id, int $opponentId): JsonResponse
    {
        if ($id === $opponentId) {
            return $this->json(
                ['detail' => 'Un joueur ne peut pas être son propre adversaire.'],
                Response::HTTP_BAD_REQUEST,
            );
        }

        $low = min($id, $opponentId);
        $high = max($id, $opponentId);

        $row = $this->connection->fetchAssociative(
            'SELECT wins_low, wins_high, updated_at FROM player_head_to_head WHERE player_low_id = ? AND player_high_id = ?',
            [$low, $high]
        );

        if ($row === false) {
            return $this->json(
                ['detail' => 'Pas de face-à-face connu entre ces deux joueurs.'],
                Response::HTTP_NOT_FOUND,
            );
        }

        [$winsPlayer, $winsOpponent] = $id === $low
            ? [(int) $row['wins_low'], (int) $row['wins_high']]
            : [(int) $row['wins_high'], (int) $row['wins_low']];

        return $this->json([
            'player_id' => $id,
            'opponent_id' => $opponentId,
            'wins_player' => $winsPlayer,
            'wins_opponent' => $winsOpponent,
            'updated_at' => $row['updated_at'],
        ]);
    }
}
