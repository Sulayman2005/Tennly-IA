<?php

namespace App\Controller;

use App\Service\PlayerComparisonService;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\ExpressionLanguage\Expression;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Security\Http\Attribute\IsGranted;

/**
 * GET /api/comparateur/analyser?joueurA=..&joueurB=..&surface=.. — vraie
 * analyse IA (probabilité, confiance, facteurs, radar) entre deux joueurs
 * choisis librement par l'utilisateur (voir ComparateurView.vue), pas
 * seulement ceux d'un match réel programmé.
 *
 * Même règle de sécurité que Prediction::class (voir Prediction.php,
 * opération Get) : réservé à l'admin OU à un utilisateur avec un abonnement
 * actif — recopiée ici via une Expression plutôt que dans security.yaml,
 * pour rester cohérent avec CheckoutSessionController (chaque action gère sa
 * propre règle plutôt que de s'appuyer sur des règles globales).
 */
#[Route('/api/comparateur/analyser', name: 'comparateur_analyser', methods: ['GET'])]
#[IsGranted(
    new Expression("is_granted('ROLE_ADMIN') or (is_granted('ROLE_USER') and user.hasActiveSubscription())"),
    message: 'Comparateur réservé aux abonnés et à l\'admin.',
)]
final class ComparateurController extends AbstractController
{
    public function __construct(
        private readonly PlayerComparisonService $playerComparisonService,
    ) {
    }

    public function __invoke(Request $request): JsonResponse
    {
        $joueurA = $request->query->get('joueurA');
        $joueurB = $request->query->get('joueurB');
        $surface = $request->query->get('surface', 'dur');

        if (!ctype_digit((string) $joueurA) || !ctype_digit((string) $joueurB)) {
            return $this->json(
                ['detail' => 'Les paramètres joueurA et joueurB sont requis (identifiants numériques).'],
                Response::HTTP_BAD_REQUEST,
            );
        }

        try {
            $resultat = $this->playerComparisonService->analyser((int) $joueurA, (int) $joueurB, (string) $surface);
        } catch (\InvalidArgumentException $e) {
            return $this->json(['detail' => $e->getMessage()], Response::HTTP_BAD_REQUEST);
        }

        return $this->json($resultat);
    }
}
