<?php

namespace App\Controller;

use App\Entity\User;
use App\Repository\PlanRepository;
use App\Service\StripeCheckoutService;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Security\Http\Attribute\IsGranted;

/**
 * POST /api/checkout-sessions — démarre un paiement Stripe pour l'utilisateur
 * COURANT (jamais à l'inscription, voir UserRegistrationProcessor). Ce
 * endpoint est appelé au moment précis où un utilisateur déjà connecté choisit
 * une formule depuis la popup paywall d'un match (voir PaywallModal.vue) :
 * un compte peut donc exister durablement sans jamais payer, et le paiement
 * n'arrive que lorsque l'utilisateur veut réellement débloquer l'analyse
 * complète d'un match précis — jamais avant, jamais automatiquement.
 *
 * `#[IsGranted('ROLE_USER')]` (et non un access_control) pour rester cohérent
 * avec le reste de l'API : chaque action gère sa propre règle de sécurité
 * plutôt que de s'appuyer sur des règles globales dans security.yaml (voir
 * AdminDashboardProvider pour le même principe côté ressources API Platform).
 */
#[Route('/api/checkout-sessions', name: 'checkout_session_create', methods: ['POST'])]
#[IsGranted('ROLE_USER')]
final class CheckoutSessionController extends AbstractController
{
    public function __construct(
        private readonly PlanRepository $planRepository,
        private readonly StripeCheckoutService $stripeCheckoutService,
    ) {
    }

    public function __invoke(Request $request): JsonResponse
    {
        $payload = json_decode($request->getContent(), true) ?? [];
        $planCode = is_string($payload['planCode'] ?? null) ? $payload['planCode'] : null;
        $redirectPath = $payload['redirectPath'] ?? null;

        $plan = $planCode ? $this->planRepository->findOneByCode($planCode) : null;
        if (null === $plan) {
            return $this->json(['detail' => 'Formule inconnue.'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        // `redirectPath` vient du client (chemin du match affiché au moment du
        // clic, voir MatchDetailView.vue/PaywallModal.vue) : on n'accepte
        // qu'un chemin interne commençant par "/" — jamais une URL absolue —
        // pour ne jamais construire une success_url/cancel_url Stripe pointant
        // vers un domaine arbitraire à partir d'une valeur envoyée par le client.
        $safeRedirectPath = (is_string($redirectPath) && str_starts_with($redirectPath, '/') && !str_starts_with($redirectPath, '//'))
            ? $redirectPath
            : '/matchs';

        /** @var User $user */
        $user = $this->getUser();

        $checkoutUrl = $this->stripeCheckoutService->createCheckoutSessionUrl($user, $plan, $safeRedirectPath);

        return $this->json(['checkoutUrl' => $checkoutUrl]);
    }
}