<?php

namespace App\Controller;

use App\Repository\SubscriptionRepository;
use App\Repository\UserRepository;
use App\Service\StripeCheckoutService;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

/**
 * GET /api/checkout-sessions/{sessionId} — statut d'un paiement Stripe,
 * public (`security: null` implicite : pas d'`#[IsGranted]`).
 *
 * Utilisé uniquement au retour de Stripe Checkout pour un paiement démarré
 * AVANT toute connexion (décision produit du 03/09/2026, voir
 * CheckoutSessionController) : le frontend (PostPaymentModal.vue) appelle
 * cet endpoint pour savoir si le paiement est bien confirmé, quel email a
 * été utilisé sur Stripe, et si un compte existe déjà pour cet email — afin
 * de proposer soit "se connecter", soit "créer mon compte", jamais les deux
 * en même temps.
 *
 * On ne fait ici confiance qu'à ce que Stripe renvoie server-side, jamais à
 * un paramètre envoyé par le frontend.
 */
final class CheckoutSessionStatusController extends AbstractController
{
    public function __construct(
        private readonly StripeCheckoutService $stripeCheckoutService,
        private readonly UserRepository $userRepository,
        private readonly SubscriptionRepository $subscriptionRepository,
    ) {
    }

    #[Route('/api/checkout-sessions/{sessionId}', name: 'checkout_session_status', methods: ['GET'])]
    public function __invoke(string $sessionId): JsonResponse
    {
        try {
            $session = $this->stripeCheckoutService->retrieveSession($sessionId);
        } catch (\Exception) {
            return $this->json(['detail' => 'Session de paiement introuvable.'], Response::HTTP_NOT_FOUND);
        }

        $email = $session->customer_details->email ?? $session->customer_email ?? null;

        $alreadyLinked = null !== $session->subscription
            && null !== $this->subscriptionRepository->findOneBy(['stripeSubscriptionId' => $session->subscription]);

        return $this->json([
            'paid' => 'paid' === $session->payment_status,
            'email' => $email,
            'planCode' => $session->metadata->plan_code ?? null,
            'alreadyLinked' => $alreadyLinked,
            'userExists' => null !== $email && null !== $this->userRepository->findOneByEmail($email),
        ]);
    }
}
